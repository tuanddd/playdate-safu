-- Run from the repository root: luajit tests/gear-mesh.lua
-- Reuses the spot/keypad regressions and their real main.lua frame dispatcher.
-- Only rendering, audio and device APIs are stubbed; timing and input ownership
-- are exercised against the implementation, including simultaneous events.
local h = dofile("tests/keypad.lua")
local e, check, test = h.env, h.check, h.test
local gear, frame, putDial = e.GearMesh, h.frame, h.putDial

local function near(a, b) return math.abs(a - b) < 1e-8 end

local function start(count, extra, enabled)
    local mods = {}
    if enabled ~= false then mods[#mods + 1] = "gear-mesh" end
    for _, id in ipairs(extra or {}) do mods[#mods + 1] = id end
    h.start(count or 3, false, mods)
    h.resetInputs()
end

local function enter(keys)
    local delta = e.Run.dirs[e.tumbler] * 0.2
    putDial(e.target - delta)
    frame(keys, delta)
    check(gear.active, "valid sweet spot entry did not start gear")
end

local function pressAt(angle)
    -- updatePlay advances the automatic gear before processing this frame's Down.
    gear.angle = (angle - gear.SPEED * 0.02) % 360
    frame({ "down" })
end

local function catchCurrent()
    enter()
    frame({})
    pressAt(0)
    check(not gear.active and gear.caughtMs == gear.CAUGHT_MS, "catch did not start confirmation")
end

local function dismiss()
    for _ = 1, 5 do frame({}, 0, 100) end
    frame({}) -- Release after the dismissal frame clears the handle guard.
    check(not gear.visible() and not gear.blockOpen, "released confirmation did not dismiss")
end

test("GEAR MESH starts clean and discovery awards no latch or target", function()
    start(3)
    check(e.Run.cfg.gearMesh and not e.Run.cfg.keypad, "GEAR MESH config did not enable its own mechanic")
    check(not gear.visible() and not gear.blockOpen, "new run inherited a gear")
    local target, picks = e.target, h.picks()
    enter()
    check(e.tumbler == 1 and e.target == target and h.picks() == picks, "discovery latched or rerolled the target")
    check(not h.events().sweetSpot and not h.events().locked, "discovery played real latch or handle feedback")
    check(gear.angle >= 120 and gear.angle <= 240, "gear starts too close to the catch")
    check(gear.visible() and gear.visualState() == "spinning", "entry has no spinning feedback")
    check(gear.blockOpen, "entry did not reserve Down")
end)

test("GEAR MESH catch window includes both 12-degree edges across zero", function()
    for _, entry in ipairs({
        { -12, true }, { -0.001, true }, { 0, true }, { 12, true },
        { 348, true }, { 359.999, true }, { 360, true }, { 372, true },
        { -12.001, false }, { 12.001, false }, { 347.999, false }, { 180, false },
    }) do
        gear.reset()
        gear.begin()
        gear.waitForRelease = false
        gear.angle = entry[1]
        local result = gear.press()
        check((result == "caught") == entry[2], "wrong catch result at " .. entry[1] .. " degrees")
        if entry[2] then
            check(not gear.active and gear.angle == 0 and gear.caughtMs == 500, "successful catch did not align and hold gear")
        else
            check(result == "miss" and gear.active and gear.missMs == 650, "outside-window press did not remain retryable")
        end
    end
end)

test("GEAR MESH rotates at 120 degrees per second independently of frame length", function()
    local final = {}
    for index, steps in ipairs({ { 1000 }, { 100, 300, 600 }, { 20, 50, 70, 860 } }) do
        gear.reset()
        gear.begin()
        gear.angle = 300
        for _, dt in ipairs(steps) do gear.update(dt) end
        final[index] = gear.angle
        check(near(gear.angle, 60), "time-based rotation changed with frame partition")
    end
    check(final[1] == final[2] and near(final[2], final[3]), "equivalent elapsed time changed gear phase")
    gear.update(3000)
    check(near(gear.angle, 60), "three-second revolution failed to wrap")
    start(3)
    enter()
    gear.angle = 300
    for _, dt in ipairs({ 20, 50, 100, 120 }) do frame({}, 0, dt) end
    check(near(gear.angle, 334.8), "real frame dispatcher did not apply elapsed play time")
end)

test("GEAR MESH misses preserve prior clicks and target under ONE SHOT", function()
    start(4, { "one-shot" })
    catchCurrent()
    dismiss()
    enter()
    frame({})
    local target, picks, latches = e.target, h.picks(), h.events().sweetSpot
    pressAt(180)
    check(gear.active and gear.visualState() == "miss", "miss did not leave spinning gear with feedback")
    check(e.tumbler == 2 and e.target == target and h.picks() == picks, "miss erased earlier click or rerolled target")
    check(h.events().sweetSpot == latches and h.events().graze == 1, "miss awarded a click or omitted feedback")
    check(e.state == e.STATE_PLAY and not h.events().locked and not h.events().fail and not h.events().reset,
        "timing miss became a premature handle pull or progress reset")
    for _ = 1, 7 do frame({}, 0, 100) end
    check(gear.active and gear.visualState() == "spinning", "miss feedback did not expire while gear kept rotating")
    pressAt(0)
    check(e.tumbler == 3 and h.events().sweetSpot == latches + 1, "retry failed to award exactly one click")
end)

test("GEAR MESH consumes entry-frame Down and held Down never repeats", function()
    for _, heldBefore in ipairs({ false, true }) do
        start(3, { "one-shot" })
        -- Hold through entry without first pulling the handle during live play.
        if heldBefore then
            h.setDocked(true)
            frame({ "down" })
            h.setDocked(false)
        end
        enter({ "down" })
        check(gear.waitForRelease and not h.events().graze and e.state == e.STATE_PLAY, "entry-frame Down escaped gear")
        gear.angle = 357.6
        frame({ "down" })
        check(gear.active and e.tumbler == 1, "held entry button caught gear without release")
        frame({})
        pressAt(180)
        check(h.events().graze == 1, "first fresh miss was not counted")
        gear.angle = 357.6
        for _ = 1, 5 do frame({ "down" }) end
        check(gear.active and e.tumbler == 1 and h.events().graze == 1, "held Down repeated a miss or caught next alignment")
        frame({})
        pressAt(0)
        check(e.tumbler == 2 and h.events().sweetSpot == 1, "fresh Down failed to catch after held miss")
    end
end)

test("other buttons do not catch a gear or pull its handle", function()
    start(3, { "one-shot" })
    enter()
    frame({})
    for _, button in ipairs({ "up", "left", "right", "a" }) do
        gear.angle = 357.6
        frame({ button })
        check(gear.active and e.tumbler == 1 and e.state == e.STATE_PLAY, "non-Down button caught gear or ended run")
        check(not h.events().sweetSpot and not h.events().locked and not h.events().graze, "non-Down button produced gameplay feedback")
        frame({})
    end
end)

test("caught gear holds 500 ms and final catch needs release plus a fresh Down to open", function()
    start(3, { "one-shot" })
    for i = 1, 3 do
        catchCurrent()
        check(e.tumbler == i + 1 and h.events().sweetSpot == i, "catch awarded wrong number of real clicks")
        check(e.state == e.STATE_PLAY and not h.events().locked, "catch Down also pulled handle")
        if i < 3 then dismiss() end
    end
    check(e.target == nil and gear.visualState() == "caught", "final catch retained target or omitted confirmation")
    for _ = 1, 4 do frame({ "down" }, 0, 120) end
    check(gear.caughtMs == 20 and gear.visible(), "confirmation failed to last until 500 ms")
    frame({ "down" })
    check(gear.caughtMs == 0 and not gear.visible() and e.state == e.STATE_PLAY, "dismissal frame opened the safe")
    for _ = 1, 3 do frame({ "down" }) end
    check(gear.blockOpen and e.state == e.STATE_PLAY and not h.events().handle, "held catch Down leaked after confirmation")
    frame({})
    frame({ "down" })
    check(e.state == e.STATE_WIN and h.events().handle == 1, "separate fresh Down failed to open safe")
end)

test("fresh Down during caught feedback is consumed and never opens early", function()
    start(3, { "one-shot" })
    catchCurrent()
    frame({})
    frame({ "down" })
    check(e.state == e.STATE_PLAY and e.tumbler == 2 and not h.events().locked, "Down during caught feedback reached ONE SHOT handle")
    dismiss()
    frame({ "down" })
    check(e.state == e.STATE_LOSE and h.events().locked == 1, "fresh early handle after confirmation failed to enforce ONE SHOT")
end)

test("GEAR MESH has no hold zone and its automatic rotation ignores crank direction", function()
    start(3)
    enter()
    frame({})
    local target, phase = e.target, gear.angle
    putDial(target + 30)
    frame({}, -0.2)
    check(gear.active and e.target == target and near(gear.angle, (phase + 2.4) % 360), "slow crank movement cancelled or reversed automatic gear")
    check(h.distance(e.dialPos, target) > 20, "active gear disconnected the main dial from the crank")
    pressAt(0)
    check(e.tumbler == 2 and h.events().sweetSpot == 1, "gear required unadvertised proximity to original spot")
end)

test("WANDERING freezes during spinning and caught gear then resumes", function()
    start(3, { "wandering" })
    enter()
    local target = e.target
    for _ = 1, 30 do frame({}) end
    check(e.target == target and gear.active, "wandering moved the pending target")
    pressAt(0)
    local nextTarget = e.target
    for _ = 1, 4 do frame({}, 0, 100) end
    check(e.target == nextTarget and gear.caughtMs == 100, "wandering moved the next target during caught feedback")
    frame({}, 0, 100)
    check(e.target ~= nextTarget and not gear.visible(), "wandering did not resume after confirmation ended")
end)

test("pause and docking freeze gear phase, feedback, target, input and clock", function()
    for _, mode in ipairs({ "docked", "paused" }) do
        for _, state in ipairs({ "spinning", "miss", "caught" }) do
            start(3, { "wandering", "one-shot" })
            enter()
            frame({})
            if state ~= "spinning" then pressAt(state == "caught" and 0 or 180); frame({}) end
            local time, target, phase, missed, caught, progress = e.remaining, e.target, gear.angle, gear.missMs, gear.caughtMs, e.tumbler
            if mode == "docked" then h.setDocked(true) else frame({ "b" }) end
            for _ = 1, 3 do frame({ "down" }, 0, 120); frame({}, 0, 120) end
            check(e.remaining == time and e.target == target, "paused/docked time or target advanced")
            check(gear.angle == phase and gear.missMs == missed and gear.caughtMs == caught, "paused/docked gear animation advanced")
            check(e.tumbler == progress and not h.events().locked, "paused/docked Down changed puzzle")
            if mode == "docked" then h.setDocked(false) else frame({ "b" }) end
            frame({})
            check(e.state == e.STATE_PLAY and e.remaining == time - 20, "paused/docked run did not resume")
            check(state == "caught" and gear.caughtMs == caught - 20 or state ~= "caught" and near(gear.angle, (phase + 2.4) % 360),
                "gear did not resume from frozen phase")
        end
    end
end)

test("overspeed cancels gear, resets real progress and consumes same-frame Down", function()
    for _, progress in ipairs({ 0, 1 }) do
        start(4, { "one-shot" })
        if progress > 0 then catchCurrent(); dismiss() end
        enter()
        frame({})
        local target, picks = e.target, h.picks()
        frame({ "down" }, (e.RESET_SPEED + 1) * 0.02)
        check(not gear.visible() and not gear.active and e.tumbler == 1, "overspeed failed to cancel gear/reset progress")
        check(h.picks() == picks + progress, "overspeed rerolled wrong number of targets")
        if progress == 0 then check(e.target == target, "zero-progress overspeed rerolled current search") end
        check(e.state == e.STATE_PLAY and not h.events().locked, "cancel-frame Down killed ONE SHOT")
        frame({ "down" })
        check(e.state == e.STATE_PLAY and gear.blockOpen, "held Down leaked after overspeed")
        frame({})
        frame({ "down" })
        check(e.state == e.STATE_LOSE, "fresh Down outside cancelled gear failed to pull handle")
    end
    start(3, { "one-shot" })
    catchCurrent()
    frame({})
    frame({ "down" }, (e.RESET_SPEED + 1) * 0.02)
    check(not gear.visible() and e.tumbler == 1 and e.state == e.STATE_PLAY, "overspeed during caught confirmation failed to reset safely")
end)

test("GEAR MESH honors SCRAMBLED directions and completes three or four spots", function()
    local sameDirection = false
    for _, count in ipairs({ 3, 4 }) do
        for _ = 1, 20 do
            start(count, { "scrambled" })
            for progress = 0, count - 1 do
                local need = e.Run.dirs[e.tumbler]
                if progress > 0 and need == e.Run.dirs[e.tumbler - 1] then sameDirection = true end
                putDial(e.target)
                frame({}, -need * 0.2)
                check(not gear.active and e.tumbler == progress + 1, "wrong direction started gear")
                catchCurrent()
                check(e.tumbler == progress + 2 and h.events().sweetSpot == progress + 1, "scrambled gear catch awarded wrong progress")
                dismiss()
            end
            frame({ "down" })
            check(e.state == e.STATE_WIN, "completed scrambled gear combination did not open")
        end
    end
    check(sameDirection, "test missed consecutive same-direction SCRAMBLED spots")
end)

test("timer expiry beats the final gear catch and run transitions clear pending state", function()
    start(3)
    for _ = 1, 2 do catchCurrent(); dismiss() end
    enter()
    frame({})
    e.remaining = 1
    pressAt(0)
    check(e.state == e.STATE_LOSE and e.loseReason == "timeup" and e.remaining == 0, "expired catch did not lose to timer")
    check(e.tumbler == 3 and h.events().sweetSpot == 2 and not h.events().locked, "expired frame accepted final catch or handle")
    check(not gear.visible() and not gear.active and gear.caughtMs == 0, "time-up left pending gear")
    start(3)
    check(not gear.visible() and not gear.blockOpen and not gear.waitForRelease, "new gear run inherited expired state")
    enter()
    e.loseRun("caught")
    check(not gear.visible() and not gear.active, "other run failure left pending gear")
    start(3)
    catchCurrent()
    start(3, nil, false)
    check(not e.Run.cfg.gearMesh and not gear.visible() and not gear.blockOpen, "ordinary run inherited caught gear or Down guard")
    frame({ "down" })
    check(h.events().locked == 1, "stale gear swallowed ordinary-run handle")
end)

test("GEAR MESH bans conflicting pairs and remains rollable with six useful modifiers", function()
    local banned = { blackout = true, nitro = true, decoy = true, keypad = true }
    for id in pairs(banned) do
        check(e.Mods.pairClass("gear-mesh", id) == e.Mods.BANNED, "unsafe gear pair allowed: " .. id)
        check(e.Mods.pairClass(id, "gear-mesh") == e.Mods.BANNED, "gear pair ban is asymmetric: " .. id)
        check(e.Mods.score({ "gear-mesh", id }) == nil, "banned gear pair has playable score")
    end
    for _, id in ipairs({ "too-loud", "scrambled", "four-tumblers", "wandering", "one-shot", "guard" }) do
        check(e.Mods.pairClass("gear-mesh", id) ~= e.Mods.BANNED, "useful gear pair banned: " .. id)
        check(e.Mods.score({ "gear-mesh", id }) ~= nil, "useful gear pair is unplayable")
    end
    local saw = false
    for _ = 1, 2000 do
        local mods = assert(e.Mods.roll(3))
        local has = {}
        for _, mod in ipairs(mods) do has[mod.id] = true end
        if has["gear-mesh"] then
            saw = true
            for id in pairs(banned) do check(not has[id], "random roll included banned gear combination: " .. id) end
            check(e.Mods.buildCfg(mods).gearMesh, "rolled gear modifier did not enable its mechanic")
        end
    end
    check(saw, "GEAR MESH never appeared in random rolls")
end)

local groups, checks = h.totals()
print(string.format("PASS %d total groups, %d invariant checks", groups, checks))
return h
