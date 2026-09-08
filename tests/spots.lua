-- Run from the repository root: luajit tests/spots.lua
-- Exercise the real placement module and main.lua state transitions. Rendering,
-- audio playback and device APIs are stubbed; gameplay functions are loaded
-- directly from source so the harness cannot silently test a copied algorithm.
local function read(path)
    local file = assert(io.open(path, "rb"))
    local contents = file:read("*a")
    file:close()
    return contents
end

local function loadInto(contents, name, env)
    local chunk = assert(loadstring(contents:gsub("%s*<const>", ""), name))
    setfenv(chunk, env)
    return chunk()
end

local source = read("source/main.lua")
local checks, groups = 0, 0
local function check(value, message)
    checks = checks + 1
    assert(value, message or "invariant failed")
end

local function test(name, fn)
    fn()
    groups = groups + 1
    print("PASS " .. name)
end

local function distance(a, b)
    return math.abs((a - b + 50) % 100 - 50)
end

local function extract(name, isGlobal)
    local prefix = isGlobal and "function " or "local function "
    local escaped = name:gsub("%.", "%%.")
    local text = assert(source:match("\n(" .. prefix .. escaped .. "%b().-\nend)"),
        "Cannot locate source function " .. name)
    return text:gsub("^local function ", "function ")
end

local events, elapsed = {}, 1000
local env = setmetatable({}, { __index = _G })
env.playdate = {
    graphics = {},
    getCurrentTimeMilliseconds = function() return elapsed end,
    startAccelerometer = function() end,
    stopAccelerometer = function() end,
}
env.pd = env.playdate
env.Run = {}
env.Sfx = setmetatable({}, { __index = function(_, key)
    return function() events[key] = (events[key] or 0) + 1 end
end })
env.Tutorial = {
    reset = function() end,
    feedback = function(_, kind) events.feedback = kind end,
}
env.sfxImages = { reset = {}, kchik = {}, kchunk = {}, locked = {}, toofast = {}, caught = {}, boom = {} }
env.placeAround = function() return 100, 100 end
env.addEffect = function() end
env.wh, env.wv = {}, {}
env.frameMs = 20

for _, name in ipairs({ "TOL", "RESET_SPEED", "DEAD_SPEED", "TICK_STEP", "GAME_MS", "WATER_N", "STATE_PLAY", "STATE_WIN", "STATE_LOSE" }) do
    local expression = assert(source:match("local " .. name .. "%s*<const>%s*=%s*([^\n]+)"),
        "Missing source constant " .. name)
    env[name] = loadInto("return " .. expression, "constant " .. name, env)
end
loadInto(read("source/spots.lua"), "source/spots.lua", env)
loadInto(read("source/modifiers.lua"), "source/modifiers.lua", env)
for _, name in ipairs({ "now", "wrapDist", "spawnTarget", "startGame", "unitsPerSec", "resetProgress", "loseRun", "openSafe", "tryHandle", "checkDecoy", "checkTumbler", "driftTargets" }) do
    loadInto(extract(name), "main.lua:" .. name, env)
end
loadInto(extract("Run.has", true), "main.lua:Run.has", env)

local pick = env.Spots.pick
local picks = 0
env.Spots.pick = function(...)
    picks = picks + 1
    return pick(...)
end

local function start(count, decoy, extras)
    local mods = {}
    if count == 4 then mods[#mods + 1] = env.Mods.byId["four-tumblers"] end
    if decoy then mods[#mods + 1] = env.Mods.byId.decoy end
    for _, id in ipairs(extras or {}) do mods[#mods + 1] = env.Mods.byId[id] end
    events, picks = {}, 0
    elapsed = elapsed + 37
    env.startGame(mods, false)
    check(env.tumbler == 1 and env.Run.cfg.tumblers == count, "wrong initial tumbler state")
    check(env.armed and env.target ~= nil, "first target must be armed")
end

local function at(position, speed, direction)
    env.dialPos = position % 100
    env.rawPos = (env.dialPos - env.posOffset) % 100
    env.checkTumbler((direction or 1) * speed * env.frameMs / 1000)
end

local function latch()
    at(env.target, 10, env.Run.dirs[env.tumbler])
end

local function clear(count)
    for _ = 1, count do latch() end
end

local function clearances(origin, decoy, target)
    check(type(target) == "number" and target >= 0 and target < 100, "target outside dial")
    check(distance(target, origin) >= env.Spots.MIN_GAP - 1e-8, "target too close to current dial")
    if decoy then check(distance(target, decoy) >= env.Spots.MIN_GAP - 1e-8, "target too close to decoy") end
end

test("placement at integer, fractional and wraparound positions", function()
    math.randomseed(78013)
    for tenth = 0, 999 do
        local origin = tenth / 10
        for decoy = 0, 99 do clearances(origin, decoy, pick(origin, decoy)) end
        clearances(origin, nil, pick(origin))
        clearances(origin, (origin + 36.05) % 100, pick(origin, (origin + 36.05) % 100))
    end
end)

test("3/4 real latches, guaranteed fixed decoy, no overlapping next target", function()
    for _, count in ipairs({ 3, 4 }) do
        for _, decoy in ipairs({ false, true }) do
            for _ = 1, 500 do
                start(count, decoy)
                local fake = env.decoyTarget
                check((fake ~= nil) == decoy, "decoy missing or added to ordinary run")
                if fake then clearances(env.dialPos, nil, fake) end
                local directions = table.concat(env.Run.dirs, ",")
                for i = 1, count do
                    local current = env.target
                    clearances(env.dialPos, fake, current)
                    latch()
                    check(env.tumbler == i + 1, "real latch did not advance once")
                    check(distance(env.dialPos, current) < 1e-8, "latch must snap onto current target")
                    check(env.decoyTarget == fake, "decoy moved after a latch")
                    check(table.concat(env.Run.dirs, ",") == directions, "latch rerolled directions")
                    if i < count then check(env.armed, "next target must be armed") end
                end
                check(env.target == nil, "real target still exists after final latch")
                check(events.sweetSpot == count, "incorrect real latch audio count")
                check(picks == count + (decoy and 1 or 0), "future or completed targets spawned unnecessarily")
                env.tryHandle()
                check(env.state == env.STATE_WIN, "completed combination did not open")
            end
        end
    end
end)

test("decoy repeats only after leaving, never changes progress or direction", function()
    start(4, true)
    local fake, real, direction = env.decoyTarget, env.target, env.Run.dirs[1]
    local shake = env.shakeStart
    for crossing = 1, 5 do
        at(fake, 10, direction)
        check(events.decoy == crossing, "decoy should click on each re-entry")
        at(fake, 10, direction)
        check(events.decoy == crossing, "decoy retriggered while remaining in its zone")
        check(env.tumbler == 1 and env.target == real and env.Run.dirs[1] == direction, "decoy changed real search")
        check(env.shakeStart == shake, "decoy shook dial")
        at((fake + 8) % 100, 10, direction)
    end
    at(fake, 10, -direction)
    check(events.decoy == 5, "decoy clicked in wrong direction")
    at(fake, 0, direction)
    check(events.decoy == 5, "stationary decoy clicked")
end)

test("fractional wraparound latches spawn relative to the snapped position", function()
    for _, position in ipairs({ 0.2, 99.8, 49.7 }) do
        for _, approach in ipairs({ -1.7, 1.7 }) do
            start(4, true, { "wandering" })
            env.target = position
            env.decoyTarget = (position + 40) % 100
            at(position + approach, 10, 1)
            check(env.tumbler == 2 and distance(env.dialPos, position) < 1e-8, "fractional latch did not snap across wrap")
            clearances(env.dialPos, env.decoyTarget, env.target)
            check(env.armed, "target spawned after fractional snap must be armed")
            local real, fake, before = env.target, env.decoyTarget, events.decoy or 0
            at(fake, 10, 1)
            check((events.decoy or 0) == before, "decoy used previous tumbler direction")
            at(fake, 10, -1)
            check(events.decoy == before + 1, "decoy ignored current counterclockwise direction")
            check(env.tumbler == 2 and env.target == real and env.Run.dirs[2] == -1, "counterclockwise decoy changed search")
        end
    end
end)

test("zero-progress errors retain target and first graze requires zone exit", function()
    for _, kind in ipairs({ "graze", "overspeed", "handle" }) do
        start(3, true)
        local current, fake, before = env.target, env.decoyTarget, picks
        env.decoyArmed = false
        if kind == "graze" then at(current, env.Run.cfg.maxEngage + 1, 1)
        elseif kind == "overspeed" then at(current, env.RESET_SPEED + 1, 1)
        else at(current, 0, 1); env.tryHandle() end
        check(env.tumbler == 1 and env.target == current and picks == before, "zero-progress error rerolled target")
        check(env.decoyTarget == fake, "zero-progress error moved decoy")
        check(not env.armed, "error inside zone must disarm current target")
        at(current, 10, 1)
        check(env.tumbler == 1, "disarmed target latched before leaving zone")
        at((current + 8) % 100, 10, 1)
        at(current, 10, 1)
        check(env.tumbler == 2, "target did not re-arm after zone exit")
    end
end)

test("partial-progress errors spawn one new armed first target", function()
    for _, count in ipairs({ 3, 4 }) do
        for progress = 1, count - 1 do
            for _, kind in ipairs({ "graze", "overspeed", "handle" }) do
                start(count, true, { "scrambled" })
                clear(progress)
                local fake, before = env.decoyTarget, picks
                local directions = table.concat(env.Run.dirs, ",")
                env.decoyArmed = false
                if kind == "graze" then at(env.target, env.Run.cfg.maxEngage + 1, env.Run.dirs[env.tumbler])
                elseif kind == "overspeed" then at(env.dialPos, env.RESET_SPEED + 1, 1)
                else env.tryHandle() end
                check(env.tumbler == 1 and picks == before + 1, "partial reset must spawn exactly one first target")
                check(env.armed, "fresh target was left disarmed")
                check(env.decoyTarget == fake, "progress reset moved decoy")
                check(table.concat(env.Run.dirs, ",") == directions, "progress reset rerolled directions")
                clearances(env.dialPos, fake, env.target)
                if kind ~= "graze" then check(not env.decoyArmed, "reset rearmed decoy in place") end
            end
        end
    end
end)

test("completion stops both spots; overspeed still resets completed progress", function()
    for _, count in ipairs({ 3, 4 }) do
        start(count, true)
        clear(count)
        local fake, before = env.decoyTarget, picks
        for _ = 1, 3 do
            at(fake, 10, env.Run.dirs[count])
            at((fake + 8) % 100, 10, env.Run.dirs[count])
        end
        check(not events.decoy and env.target == nil and picks == before, "spot fired or spawned after completion")
        at(env.dialPos, env.Run.cfg.maxEngage + 1, 1)
        check(env.tumbler == count + 1, "graze speed reset without an active target")
        at(env.dialPos, env.RESET_SPEED + 1, 1)
        check(env.tumbler == 1 and env.armed and picks == before + 1, "overspeed did not restart completed progress")
        check(env.decoyTarget == fake, "completed reset moved decoy")
        clearances(env.dialPos, fake, env.target)
    end
end)

test("ONE SHOT loses on early A and opens on completed A", function()
    for _, count in ipairs({ 3, 4 }) do
        for progress = 0, count do
            start(count, true, { "one-shot" })
            clear(progress)
            local before = picks
            env.tryHandle()
            check(env.state == (progress == count and env.STATE_WIN or env.STATE_LOSE), "ONE SHOT chose wrong outcome")
            check(picks == before, "ONE SHOT unnecessarily spawned another target")
        end
    end
end)

test("SCRAMBLED honors each rolled direction including consecutive equal turns", function()
    local sawSame = false
    for _ = 1, 100 do
        start(4, true, { "scrambled" })
        for i = 1, 4 do
            local current, need = env.target, env.Run.dirs[i]
            if i > 1 and need == env.Run.dirs[i - 1] then sawSame = true end
            at(current, 10, -need)
            check(env.tumbler == i and env.target == current, "wrong direction latched")
            at(current, 10, need)
            check(env.tumbler == i + 1, "correct scrambled direction failed")
        end
    end
    check(sawSame, "test never exercised consecutive same-direction targets")
end)

test("WANDERING wraps and reflects with clearance even for large steps", function()
    math.randomseed(39017)
    for _, fake in ipairs({ 0, 0.1, 17.9, 50, 99.9 }) do
        for _, sign in ipairs({ -1, 1 }) do
            local position = pick((fake + 50) % 100, fake)
            for i = 1, 4000 do
                local amount = i % 19 == 0 and 271.37 or 0.6
                position, sign = env.Spots.drift(position, fake, amount, sign)
                check(position >= 0 and position < 100, "drift left dial")
                check(distance(position, fake) >= env.Spots.MIN_GAP - 1e-8, "drift entered decoy clearance")
                check(sign == 1 or sign == -1, "drift returned invalid direction")
            end
            local near = (fake + env.Spots.MIN_GAP + 0.1) % 100
            local reflected, nextSign = env.Spots.drift(near, fake, 0.6, -1)
            check(nextSign == 1 and distance(reflected, near) > 0, "drift stuck instead of reflecting")
        end
    end
    for _, sign in ipairs({ -1, 1 }) do
        local position, resultSign = env.Spots.drift(99.9, nil, 321.7, sign)
        check(distance(position, (99.9 + 321.7 * sign) % 100) < 1e-8 and resultSign == sign, "unrestricted drift did not wrap")
    end
end)

test("WANDERING freezes during turning and cannot latch while stationary", function()
    start(3, true, { "wandering" })
    local current, fake = env.target, env.decoyTarget
    env.driftTargets(120, env.DEAD_SPEED)
    check(env.target == current, "target drifted while dial was turning")
    env.driftTargets(120, 0)
    check(env.target ~= current and env.decoyTarget == fake, "only active real target should drift")
    at(env.target, 0, 1)
    check(env.tumbler == 1 and not events.sweetSpot, "stationary wandering target latched")
    at(env.target, 10, 1)
    check(env.tumbler == 2, "wandering target did not latch once crank moved")
    clear(2)
    env.driftTargets(120, 0)
    check(env.target == nil and env.tumbler == 4, "drift revived completed target")
end)

print(string.format("PASS %d groups, %d invariant checks", groups, checks))
