-- Run from the repository root: luajit tests/keypad.lua
-- Includes the ordinary spot regression suite, then drives the actual frame
-- dispatcher with synthetic crank movement and fresh/held button states.
local h = dofile("tests/spots.lua")
local e, check, test = h.env, h.check, h.test
local keypad = e.Keypad
local held, previous, crank, docked = {}, {}, 0, false

for index, name in ipairs({ "Left", "Right", "Up", "Down", "B", "A" }) do
    e.pd["kButton" .. name] = 2 ^ (index - 1)
end
local buttons = {
    up = e.pd.kButtonUp, down = e.pd.kButtonDown,
    left = e.pd.kButtonLeft, right = e.pd.kButtonRight,
    a = e.pd.kButtonA, b = e.pd.kButtonB,
}
e.pd.buttonJustPressed = function(button) return held[button] and not previous[button] or false end
e.pd.buttonIsPressed = function(button) return held[button] or false end
e.pd.isCrankDocked = function() return docked end
e.pd.getCrankChange = function() local value = crank; crank = 0; return value end
e.pd.timer = { updateTimers = function() end }
e.gfx = e.pd.graphics
e.gfx.setColor = function() end
e.gfx.getDisplayImage = function() return {} end

for _, name in ipairs({ "DEG_PER_UNIT", "STATE_TITLE", "STATE_MENU", "STATE_TOTITLE", "BLACKOUT_LIT_MS", "BLACKOUT_FADE_MS", "BLACKOUT_DARK_MS", "BLACKOUT_CLICK_MS", "BLACKOUT_MS" }) do
    local expression = assert(h.source:match("local " .. name .. "%s*<const>%s*=%s*([^\n]+)"),
        "Missing source constant " .. name)
    e[name] = h.loadInto("return " .. expression, "constant " .. name, e)
end
for _, name in ipairs({ "doTicks", "updateGuard", "updateNitro", "updateSlosh", "updateNotes", "perfSample",
    "drawScene", "drawLose", "drawDockedNotice", "drawMenu", "drawWin", "drawTitle", "drawToTitle", "updateWin", "updateLose" }) do
    e[name] = function() end
end
for _, name in ipairs({ "readCrank", "updatePlay", "openMenu", "closeMenu", "updateMenu" }) do
    h.loadInto(h.extract(name), "main.lua:" .. name, e)
end
h.loadInto(assert(h.source:match("(Keypad%.buttons%s*=%s*%b{})")), "main.lua:Keypad.buttons", e)
h.loadInto(h.extract("Keypad.updateInput", true), "main.lua:Keypad.updateInput", e)
h.loadInto(h.extract("pd.update", true), "main.lua:pd.update", e)
e.MENU_ITEMS = { "Resume", "Modifiers", "Debug", "Quit" }

local function frame(keys, delta)
    held = {}
    for _, name in ipairs(keys or {}) do held[assert(buttons[name], "Unknown button " .. name)] = true end
    crank = (delta or 0) * e.DEG_PER_UNIT
    h.advance(20)
    e.pd.update()
    previous = held
end

local function resetInputs()
    held, previous, crank, docked = {}, {}, 0, false
    e.lastTime = h.advance(20)
end

local function start(count, extra, enabled)
    local mods = {}
    if enabled ~= false then mods[#mods + 1] = "keypad" end
    for _, id in ipairs(extra or {}) do mods[#mods + 1] = id end
    h.start(count or 3, false, mods)
    resetInputs()
end

local function putDial(position)
    e.dialPos = position % 100
    e.rawPos = (e.dialPos - e.posOffset) % 100
end

local function enter(keys)
    local delta = e.Run.dirs[e.tumbler] * 0.2
    putDial(e.target - delta)
    frame(keys, delta)
    check(keypad.active, "valid sweet spot entry did not open keypad")
end

local function tap(direction)
    frame({})
    frame({ direction })
end

local function sequenceString()
    return table.concat(keypad.sequence, ",")
end

local function completeCurrent(last)
    keypad.sequence = { "up", "right", "left", last or "down" }
    enter()
    frame({})
    for _, direction in ipairs({ "up", "right", "left", last or "down" }) do tap(direction) end
end

test("KEYPAD sequences contain four valid arrows and reset for each real spot", function()
    math.randomseed(83142)
    local allowed = { up = true, down = true, left = true, right = true }
    for _ = 1, 1000 do
        keypad.reset()
        keypad.newSpot()
        check(#keypad.sequence == keypad.LENGTH and keypad.LENGTH == 4, "incorrect keypad length")
        for _, direction in ipairs(keypad.sequence) do check(allowed[direction], "invalid keypad arrow") end
        keypad.begin()
        check(keypad.active and keypad.progress == 0 and keypad.waitForRelease, "keypad entry did not start clean")
        check(keypad.blockOpen, "entry must reserve Down for keypad")
        local code = sequenceString()
        keypad.waitForRelease = false
        keypad.press(keypad.sequence[1])
        check(keypad.progress == 1, "first correct arrow did not advance input")
        keypad.cancel()
        check(not keypad.active and keypad.progress == 0 and sequenceString() == code, "cancel discarded code or retained input")
        check(keypad.blockOpen, "cancel removed release guard")
        keypad.newSpot()
        check(not keypad.active and keypad.progress == 0 and keypad.blockOpen, "new spot lost release guard")
        keypad.reset()
        check(not keypad.active and keypad.progress == 0 and not keypad.blockOpen, "new run inherited keypad state")
    end
end)

test("entering KEYPAD gives no real latch; four arrows earn exactly one", function()
    start(3)
    keypad.sequence = { "up", "right", "left", "down" }
    local target, picks = e.target, h.picks()
    enter()
    check(e.tumbler == 1 and e.target == target and h.picks() == picks, "entry awarded or rerolled real spot")
    check(not h.events().sweetSpot, "entry played success sound before code was completed")
    frame({})
    for i, direction in ipairs({ "up", "right", "left" }) do
        tap(direction)
        check(keypad.active and keypad.progress == i and e.tumbler == 1, "partial code awarded progress")
    end
    tap("down")
    check(e.tumbler == 2 and not keypad.active, "complete code did not earn one real latch")
    check(h.events().sweetSpot == 1 and h.picks() == picks + 1, "code completion duplicated latch or target")
    check(e.state == e.STATE_PLAY and not h.events().locked, "final Down also pulled handle")
end)

test("wrong arrow and direction chords reset only the current code", function()
    for _, badKeys in ipairs({ { "left" }, { "right", "down" } }) do
        start(4, { "one-shot" })
        completeCurrent()
        frame({})
        keypad.sequence = { "up", "right", "left", "down" }
        enter()
        tap("up")
        local target, picks, code = e.target, h.picks(), sequenceString()
        frame({})
        frame(badKeys)
        check(keypad.active and keypad.progress == 0 and keypad.failed, "wrong input did not reset current code")
        check(e.tumbler == 2 and e.target == target and h.picks() == picks, "wrong input erased earned latch or moved target")
        check(sequenceString() == code and e.state == e.STATE_PLAY, "wrong input rerolled code or ended ONE SHOT")
        check(not h.events().locked and not h.events().reset and not h.events().fail, "wrong arrow used handle/reset/fail feedback")
        check((h.events().keypadError or 0) == 1, "wrong arrow must play error sound once")
        frame(badKeys)
        check((h.events().keypadError or 0) == 1, "held invalid input repeated error sound")
        tap("up")
        check(keypad.progress == 1 and not keypad.failed, "correct retry did not clear error state")
    end
end)

test("held directions never enter or repeat keypad input without a fresh press", function()
    start(3)
    keypad.sequence = { "up", "up", "left", "down" }
    frame({ "up" })
    enter({ "up" })
    frame({ "up" })
    check(keypad.progress == 0 and keypad.waitForRelease, "button held before entry counted as input")
    frame({})
    frame({ "up" })
    check(keypad.progress == 1, "fresh direction did not count")
    for _ = 1, 8 do frame({ "up" }) end
    check(keypad.progress == 1, "held direction repeated")
    tap("up")
    check(keypad.progress == 2, "releasing and repressing repeated arrow did not count")
end)

test("adding a fresh direction while another is held is one invalid chord", function()
    start(3, { "one-shot" })
    keypad.sequence = { "up", "right", "left", "down" }
    enter()
    tap("up")
    frame({ "up", "right" })
    check(keypad.progress == 0 and keypad.failed and keypad.waitForRelease, "held plus fresh chord was accepted")
    check(h.events().keypadError == 1 and e.state == e.STATE_PLAY, "chord feedback or ONE SHOT outcome incorrect")
    frame({ "right" })
    check(keypad.progress == 0 and keypad.waitForRelease, "partial chord release enabled another guess")
    tap("up")
    check(keypad.progress == 1, "releasing all chord buttons did not permit retry")
end)

test("all final arrows are consumed and final Down requires release plus a new Down", function()
    for _, last in ipairs({ "up", "right", "left", "down" }) do
        start(3, { "one-shot" })
        for i = 1, 3 do
            completeCurrent(last)
            check(e.tumbler == i + 1 and e.state == e.STATE_PLAY, "code-ending arrow escaped to handle")
            for _ = 1, 3 do frame({ last }) end
            check(e.tumbler == i + 1 and e.state == e.STATE_PLAY, "held ending arrow pulled handle")
            frame({})
        end
        check(e.target == nil and not keypad.active, "completed run left an input target")
        frame({ "a" })
        check(e.state == e.STATE_PLAY, "A still opens the safe during play")
        frame({})
        frame({ "down" })
        check(e.state == e.STATE_WIN, "separate fresh Down did not open completed safe")
    end
end)

test("leaving keypad proximity cancels only input and consumes same-frame Down", function()
    for _, direction in ipairs({ -1, 1 }) do
        start(4, { "one-shot" })
        completeCurrent()
        frame({})
        keypad.sequence = { "up", "right", "left", "down" }
        enter()
        tap("up")
        frame({})
        local target, code, picks = e.target, sequenceString(), h.picks()
        putDial(target + direction * (keypad.HOLD_TOL - 0.1))
        frame({ "down" }, direction * 0.2)
        check(not keypad.active and keypad.progress == 0, "leaving proximity did not cancel input")
        check(e.tumbler == 2 and e.target == target and h.picks() == picks, "leaving keypad erased earned progress")
        check(e.state == e.STATE_PLAY and not h.events().locked, "cancel-frame Down pulled handle or killed ONE SHOT")
        check(sequenceString() == code, "proximity cancellation rerolled code")
        frame({ "down" })
        check(e.state == e.STATE_PLAY, "held Down escaped after proximity cancellation")
        frame({})
        enter()
        check(keypad.progress == 0 and sequenceString() == code, "re-entry did not restart same code")
    end
end)

test("overspeed cancellation consumes Down even when progress and code are reset", function()
    for _, progress in ipairs({ 0, 1 }) do
        start(3, { "one-shot" })
        if progress == 1 then completeCurrent(); frame({}) end
        enter()
        frame({})
        local before = h.picks()
        frame({ "down" }, (e.RESET_SPEED + 1) * 0.02)
        check(not keypad.active and e.tumbler == 1, "overspeed failed to cancel pending keypad")
        check(e.state == e.STATE_PLAY and not h.events().locked, "overspeed-frame Down killed ONE SHOT")
        check(h.picks() == before + progress, "overspeed rerolled wrong number of targets")
        frame({ "down" })
        check(e.state == e.STATE_PLAY, "held Down escaped after overspeed cancellation")
    end
end)

test("Down outside keypad pulls handle, A is inert, and held Down does not repeat", function()
    for _, enabled in ipairs({ false, true }) do
        start(3, nil, enabled)
        local target = e.target
        frame({ "a" })
        check(not h.events().locked and e.target == target and e.tumbler == 1, "A pulled handle")
        frame({})
        frame({ "down" })
        check(h.events().locked == 1 and e.tumbler == 1, "Down outside keypad did not pull handle")
        for _ = 1, 3 do frame({ "down" }) end
        check(h.events().locked == 1, "held Down repeatedly pulled handle")
    end
    start(3, { "one-shot" })
    frame({ "down" })
    check(e.state == e.STATE_LOSE, "fresh early Down did not enforce ONE SHOT")
end)

test("docking and pause freeze keypad input, handle input, clock and wandering", function()
    for _, mode in ipairs({ "docked", "paused" }) do
        start(3, { "wandering" })
        keypad.sequence = { "up", "right", "left", "down" }
        enter()
        tap("up")
        frame({})
        local time, target = e.remaining, e.target
        if mode == "docked" then docked = true else frame({ "b" }) end
        frame({ "right" })
        frame({ "down" })
        check(keypad.active and keypad.progress == 1, "paused/docked direction changed keypad")
        check(e.remaining == time and e.target == target, "paused/docked run advanced clock or wandering")
        check(not h.events().locked, "paused/docked Down pulled handle")
        if mode == "docked" then docked = false else frame({}); frame({ "b" }) end
        frame({})
        frame({ "right" })
        check(e.state == e.STATE_PLAY and keypad.progress == 2, "keypad could not resume after pause/dock")
    end
    start(3, { "one-shot" })
    docked = true
    frame({ "down" })
    check(e.state == e.STATE_PLAY and not h.events().locked, "docked Down killed ONE SHOT outside keypad")
end)

test("WANDERING freezes during keypad and resumes after cancellation", function()
    start(3, { "wandering", "guard" })
    enter()
    local target = e.target
    for _ = 1, 100 do frame({}) end
    check(e.target == target and keypad.active, "wandering moved target during keypad entry")
    putDial(target + keypad.HOLD_TOL + 1)
    frame({})
    check(not keypad.active, "lost proximity did not cancel wandering keypad")
    local afterCancel = e.target
    frame({})
    check(e.target ~= afterCancel, "wandering did not resume after keypad cancellation")
end)

test("KEYPAD honors SCRAMBLED direction and completes three or four real spots", function()
    for _, count in ipairs({ 3, 4 }) do
        start(count, { "scrambled" })
        for progress = 0, count - 1 do
            local need = e.Run.dirs[e.tumbler]
            putDial(e.target)
            frame({}, -need * 0.2)
            check(not keypad.active and e.tumbler == progress + 1, "wrong crank direction opened keypad")
            local code = { unpack(keypad.sequence) }
            enter()
            frame({})
            for _, direction in ipairs(code) do tap(direction) end
            check(e.tumbler == progress + 2 and h.events().sweetSpot == progress + 1, "keypad/scrambled latch count incorrect")
            frame({})
        end
        frame({ "down" })
        check(e.state == e.STATE_WIN, "completed keypad/scrambled safe did not open")
    end
end)

test("timer expiry takes priority over final arrow and new runs clear pending state", function()
    start(3)
    keypad.sequence = { "up", "right", "left", "down" }
    enter()
    for _, direction in ipairs({ "up", "right", "left" }) do tap(direction) end
    frame({})
    e.remaining = 1
    frame({ "down" })
    check(e.state == e.STATE_LOSE and not keypad.active and keypad.progress == 0, "timer expiry left keypad active")
    check(e.tumbler == 1 and not h.events().sweetSpot and not h.events().locked, "expired frame accepted final arrow or handle")
    start(3)
    check(not keypad.active and not keypad.failed and not keypad.blockOpen and keypad.progress == 0, "new keypad run inherited expired input")
    enter()
    tap(keypad.sequence[1])
    start(3, nil, false)
    check(not keypad.active and keypad.sequence == nil and not keypad.blockOpen, "ordinary run inherited pending keypad")
    frame({ "down" })
    check(h.events().locked == 1, "stale keypad guard swallowed ordinary run handle")
end)

test("KEYPAD incompatibilities are banned while useful combinations remain rollable", function()
    for _, id in ipairs({ "blackout", "nitro", "decoy" }) do
        check(e.Mods.pairClass("keypad", id) == e.Mods.BANNED, "unsafe keypad pair was allowed: " .. id)
        check(e.Mods.score({ "keypad", id }) == nil, "banned keypad pair had playable score")
    end
    for _, id in ipairs({ "too-loud", "scrambled", "four-tumblers", "wandering", "one-shot", "guard" }) do
        check(e.Mods.pairClass("keypad", id) ~= e.Mods.BANNED, "useful keypad pair was banned: " .. id)
    end
    for first = 1, #e.Mods.list - 2 do
        for second = first + 1, #e.Mods.list - 1 do
            for third = second + 1, #e.Mods.list do
                local ids = { e.Mods.list[first].id, e.Mods.list[second].id, e.Mods.list[third].id }
                local blocked = false
                for i = 1, 2 do
                    for j = i + 1, 3 do
                        if e.Mods.pairClass(ids[i], ids[j]) == e.Mods.BANNED then blocked = true end
                    end
                end
                check((e.Mods.score(ids) == nil) == blocked, "triple scoring ignored pair compatibility")
            end
        end
    end
    local saw = false
    for _ = 1, 2000 do
        local mods = assert(e.Mods.roll(3))
        local has = {}
        for _, mod in ipairs(mods) do has[mod.id] = true end
        if has.keypad then
            saw = true
            check(not has.blackout and not has.nitro and not has.decoy, "random roll included banned keypad combination")
            check(e.Mods.buildCfg(mods).keypad, "rolled KEYPAD did not enable config")
        end
    end
    check(saw, "KEYPAD never appeared in random rolls")
end)

local groups, checks = h.totals()
print(string.format("PASS %d total groups, %d invariant checks", groups, checks))
