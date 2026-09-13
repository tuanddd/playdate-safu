-- Run from the repository root: luajit tests/dust-jam.lua
-- Includes the spot, keypad and gear regressions. The actual DustJam module
-- and main.lua dispatcher own calibration, input ordering and real latches;
-- only microphone hardware, graphics and sound playback are simulated.
local h = dofile("tests/gear-mesh.lua")
local e, check, test = h.env, h.check, h.test
local dust, frame, putDial = e.DustJam, h.frame, h.putDial
local mic = {}

local function near(a, b) return math.abs(a - b) < 1e-8 end

local function installMic(options)
    options = options or {}
    mic = { requests = 0, starts = 0, stops = 0, reads = 0, level = options.level or 0.01 }
    e.pd.sound.micinput = {
        requestAccess = function(message)
            mic.requests = mic.requests + 1
            mic.message = message
            if options.yieldMs then h.advance(options.yieldMs) end
            if options.requestError then error("Permission unavailable") end
        end,
        startListening = function(source)
            mic.starts = mic.starts + 1
            mic.source = source
            if options.startError then error("No microphone") end
            return not options.denied
        end,
        stopListening = function() mic.stops = mic.stops + 1 end,
        getLevel = function()
            mic.reads = mic.reads + 1
            if options.readError then error("Disconnected") end
            return mic.level
        end,
    }
end

local function start(count, extra, options, enabled)
    dust.suspend()
    installMic(options)
    local mods = {}
    if enabled ~= false then mods[#mods + 1] = "dust-jam" end
    for _, id in ipairs(extra or {}) do mods[#mods + 1] = id end
    h.start(count or 3, false, mods)
    h.resetInputs()
end

local function enter(keys)
    local delta = e.Run.dirs[e.tumbler] * 0.2
    putDial(e.target - delta)
    frame(keys, delta)
    check(dust.active, "valid sweet spot entry did not reveal a jammed pin")
end

local function holdUntilClear(keys)
    local frames = 0
    while dust.active and frames < 100 do
        frame(keys or { "up" })
        frames = frames + 1
    end
    check(not dust.active and dust.clearedMs > 0, "sustained input failed to clear dust")
    return frames
end

local function clearCurrent()
    enter()
    frame({})
    holdUntilClear()
end

local function dismiss()
    for _ = 1, 6 do frame({}, 0, 100) end
    frame({})
    check(not dust.visible() and not dust.blockOpen, "released dust confirmation failed to dismiss")
end

local function calibrated(level)
    dust.reset()
    installMic({ level = level })
    dust.begin()
    dust.enableMic()
    dust.update(dust.SETTLE_MS, false, level)
    dust.update(dust.CALIBRATE_MS, false, level)
    check(dust.listening and dust.micState == "listening", "microphone did not finish calibration")
end

test("DUST JAM discovery defers the real latch and starts microphone input automatically", function()
    start(3)
    check(e.Run.cfg.dustJam and not e.Run.cfg.keypad and not e.Run.cfg.gearMesh, "dust config did not enable its own mechanic")
    check(not dust.visible() and not dust.blockOpen and dust.micState == "off", "new run inherited dust or microphone state")
    local target, picks = e.target, h.picks()
    enter()
    check(e.tumbler == 1 and e.target == target and h.picks() == picks, "discovery awarded or rerolled a real latch")
    check(not h.events().sweetSpot and not h.events().locked, "discovery played latch or handle feedback")
    check(mic.requests == 1 and mic.starts == 1 and mic.reads == 1 and dust.listening,
        "first jam did not automatically request access and start the device microphone")
    check(dust.micState == "calibrating" and dust.progress == 0, "automatic microphone entry skipped calibration")
    frame({})
    holdUntilClear()
    check(e.tumbler == 2 and h.events().sweetSpot == 1 and h.picks() == picks + 1,
        "clearing dust did not award exactly one real latch")
    check(mic.requests == 1 and mic.starts == 1 and mic.stops == 1 and not dust.listening,
        "Up completion repeated permission or left the automatic microphone listening")
end)

test("automatic microphone access waits for a real jam and never starts in other modifiers or pause", function()
    for _, extra in ipairs({ {}, { "spotlight" }, { "keypad" }, { "gear-mesh" } }) do
        start(3, extra, nil, false)
        frame({ "a" })
        local delta = e.Run.dirs[e.tumbler] * 0.2
        putDial(e.target - delta)
        frame({}, delta)
        frame({ "a" })
        check(mic.requests == 0 and mic.starts == 0 and not dust.listening,
            "non-DUST JAM modifier requested microphone access")
    end
    start(3)
    for _ = 1, 10 do frame({ "a" }) end
    check(mic.requests == 0 and mic.starts == 0, "searching requested microphone access before finding a pin")
    h.setDocked(true)
    for _ = 1, 5 do frame({ "a" }, 1) end
    check(mic.requests == 0 and mic.starts == 0, "docked input started microphone access")
    h.setDocked(false)
    frame({})
    frame({ "b" })
    for _ = 1, 5 do frame({}) end
    check(e.state == e.STATE_MENU and mic.requests == 0 and mic.starts == 0, "pause menu started microphone access")
    frame({ "b" })
    frame({})
    enter()
    check(mic.requests == 1 and mic.starts == 1, "resumed real discovery did not start automatic microphone input")
end)

test("A is inert during automatic DUST JAM listening", function()
    start(3, { "one-shot" })
    enter()
    local target, requests, starts = e.target, mic.requests, mic.starts
    for _ = 1, 3 do frame({}); frame({ "a" }); frame({ "a" }) end
    check(mic.requests == requests and mic.starts == starts and dust.listening,
        "A repeated microphone permission or restarted its session")
    check(dust.active and dust.progress == 0 and e.target == target and e.tumbler == 1,
        "A cleared dust or changed the pending pin")
    check(e.state == e.STATE_PLAY and not h.events().locked and not h.events().sweetSpot,
        "A pulled the handle or earned a real latch")
end)

test("dust clearing preserves partial progress across separated holds and breaths", function()
    start(3)
    enter()
    frame({})
    for _ = 1, 12 do frame({ "up" }) end
    local partial, target, picks = dust.progress, e.target, h.picks()
    check(partial > 0 and partial < 1 and e.tumbler == 1, "partial hold latched or did not clear any dust")
    for _ = 1, 20 do frame({}) end
    check(dust.progress == partial and e.target == target and h.picks() == picks, "rest restored dust or changed the pending spot")
    holdUntilClear()
    check(e.tumbler == 2 and h.events().sweetSpot == 1, "resumed hold did not finish one pin")
    calibrated(0.01)
    for _ = 1, 15 do dust.update(20, false, 0.3) end
    partial = dust.progress
    for _ = 1, 30 do dust.update(20, false, 0.01) end
    check(partial > 0 and dust.progress == partial and dust.active, "quiet interval lost partial microphone clearing")
    for _ = 1, 15 do dust.update(20, false, 0.3) end
    check(dust.progress > partial and dust.active, "second puff could not continue the first")
end)

test("Up held before discovery must be released before it can clear dust", function()
    start(3)
    frame({ "up" })
    enter({ "up" })
    for _ = 1, 20 do frame({ "up" }) end
    check(dust.waitForRelease and dust.progress == 0 and e.tumbler == 1, "held entry Up counted as a fresh action")
    frame({})
    frame({ "up" })
    check(not dust.waitForRelease and dust.progress > 0, "fresh hold did not start after release")
end)

test("DUST JAM owns entry, active and confirmation Down under ONE SHOT", function()
    start(3, { "one-shot" })
    enter({ "down" })
    check(e.state == e.STATE_PLAY and dust.blockOpen and not h.events().locked, "entry Down pulled the handle")
    frame({})
    frame({ "down" })
    check(dust.active and dust.progress == 0 and e.state == e.STATE_PLAY, "active Down cleared dust or ended run")
    frame({})
    holdUntilClear({ "up", "down" })
    check(e.tumbler == 2 and e.state == e.STATE_PLAY and not h.events().locked, "clearing-frame Down escaped to handle")
    frame({})
    frame({ "down" })
    check(e.state == e.STATE_PLAY and not h.events().locked, "fresh confirmation Down reached ONE SHOT")
    for _ = 1, 6 do frame({ "down" }, 0, 100) end
    check(not dust.visible() and dust.blockOpen and e.state == e.STATE_PLAY, "held Down escaped at confirmation expiry")
    frame({})
    frame({ "down" })
    check(e.state == e.STATE_LOSE and h.events().locked == 1, "fresh early handle after release did not enforce ONE SHOT")
end)

test("final dust clearing requires a separate Down after confirmation", function()
    for _, count in ipairs({ 3, 4 }) do
        start(count, { "scrambled", "one-shot" })
        for i = 1, count do
            clearCurrent()
            check(e.tumbler == i + 1 and h.events().sweetSpot == i and e.state == e.STATE_PLAY,
                "dust clearing awarded the wrong number of real clicks")
            if i < count then dismiss() end
        end
        check(e.target == nil and dust.clearedMs > 0, "final cleared pin retained target or omitted feedback")
        frame({ "down" })
        for _ = 1, 6 do frame({ "down" }, 0, 100) end
        check(e.state == e.STATE_PLAY and not h.events().handle, "held final Down automatically opened safe")
        frame({})
        frame({ "down" })
        check(e.state == e.STATE_WIN and h.events().handle == 1 and not dust.listening,
            "fresh final Down failed to open completed safe")
    end
end)

test("overspeed cancels dust and consumes Down without an accidental handle pull", function()
    for _, progress in ipairs({ 0, 1 }) do
        start(4, { "one-shot" })
        if progress > 0 then clearCurrent(); dismiss() end
        enter()
        frame({})
        frame({ "up" })
        local target, picks = e.target, h.picks()
        frame({ "down" }, (e.RESET_SPEED + 1) * 0.02)
        check(not dust.visible() and dust.progress == 0 and e.tumbler == 1, "overspeed failed to cancel dust and reset progress")
        check(h.picks() == picks + progress, "dust overspeed rerolled the wrong number of targets")
        if progress == 0 then check(e.target == target, "zero-progress overspeed moved pending target") end
        check(e.state == e.STATE_PLAY and not h.events().locked, "cancel-frame Down killed ONE SHOT")
        frame({ "down" })
        check(dust.blockOpen and e.state == e.STATE_PLAY, "held Down escaped after cancellation")
        frame({})
        frame({ "down" })
        check(e.state == e.STATE_LOSE, "fresh Down outside cancelled dust failed to pull handle")
    end
end)

test("dust has no hidden hold zone and WANDERING pauses during inspection", function()
    start(3, { "wandering" })
    enter()
    local target = e.target
    for _ = 1, 30 do frame({}) end
    check(dust.active and e.target == target, "wandering moved the jammed pin's target")
    putDial(target + 30)
    frame({}, -0.2)
    check(dust.active and e.target == target, "ordinary crank movement cancelled dust inspection")
    holdUntilClear()
    local nextTarget = e.target
    for _ = 1, 5 do frame({}, 0, 100) end
    check(e.target == nextTarget and dust.clearedMs == 50, "wandering moved during cleared confirmation")
    frame({}, 0, 100)
    frame({}) -- Confirmation owns its dismissal frame before wandering resumes.
    check(not dust.visible() and e.target ~= nextTarget, "wandering failed to resume after pin confirmation")
end)

test("microphone calibration ignores initial sound and rejects steady noise and short spikes", function()
    dust.reset()
    installMic()
    dust.begin()
    dust.enableMic()
    check(mic.requests == 1 and mic.starts == 1 and mic.source == "device", "microphone setup did not request the device input")
    dust.update(dust.SETTLE_MS, false, 0.9)
    check(dust.progress == 0 and dust.calMs == 0, "initial settling sound contaminated calibration or cleared dust")
    dust.update(dust.CALIBRATE_MS, false, 0.2)
    check(dust.micState == "listening" and near(dust.baseline, 0.2) and dust.progress == 0,
        "ambient calibration awarded progress or measured wrong baseline")
    for _ = 1, 50 do dust.update(20, false, 0.22) end
    check(dust.progress == 0, "steady ambient noise cleared dust")
    for _ = 1, 3 do dust.update(20, false, 0.9) end
    check(dust.progress == 0, "60 ms spike passed the 80 ms microphone gate")
    dust.update(20, false, 0.2)
    check(dust.hotMs == 0 and dust.progress == 0, "quiet frame failed to clear spike history")
    for _ = 1, 4 do dust.update(20, false, 0.9) end
    check(dust.progress > 0 and dust.blowing, "sustained puff failed to pass the gate")
    local partial = dust.progress
    dust.suppressMic(200)
    for _ = 1, 9 do dust.update(20, false, 0.9) end
    check(dust.progress == partial, "suppressed speaker audio continued microphone clearing")
end)

test("GUARD speaker suppression survives discovery and pauses microphone calibration", function()
    start(3, { "guard" })
    local updateGuard, addDrop = e.updateGuard, e.addDrop
    for _, name in ipairs({ "GUARD_MARK_MS", "GUARD_GRACE_MS" }) do
        local expression = assert(h.source:match("local " .. name .. "%s*<const>%s*=%s*([^\n]+)"))
        e[name] = h.loadInto("return " .. expression, "constant " .. name, e)
    end
    e.addDrop = function() end
    h.loadInto(h.extract("updateGuard"), "main.lua:updateGuard", e)
    e.guardAt = h.advance(0)
    e.updateGuard(0)
    check(h.events().footstep == 1 and dust.suppressMs == 1800 and not dust.active,
        "inactive GUARD footstep did not suppress its full sample and tail")
    for _ = 1, 5 do frame({}, 0, 100) end
    check(dust.suppressMs == 1300 and not dust.active, "speaker suppression did not age during 500 ms of searching")
    dust.begin()
    dust.enableMic()
    check(dust.suppressMs == 1300 and dust.listening and dust.micState == "calibrating",
        "discovering the pin discarded an already-playing footstep's suppression")
    for _ = 1, 65 do
        dust.update(20, false, 0.95)
        check(dust.progress == 0 and dust.calMs == 0 and dust.noiseSum == 0 and dust.hotMs == 0,
            "suppressed footstep cleared dust or contaminated ambient calibration")
    end
    check(dust.suppressMs == 0 and dust.micState == "calibrating", "suppression did not finish in active time")
    dust.update(dust.SETTLE_MS, false, 0.01)
    dust.update(dust.CALIBRATE_MS, false, 0.01)
    check(dust.micState == "listening" and near(dust.baseline, 0.01) and dust.progress == 0,
        "quiet settling and calibration failed after the footstep ended")
    for _ = 1, 4 do dust.update(20, false, 0.35) end
    check(dust.progress > 0, "speaker suppression remained stuck after quiet calibration")
    e.updateGuard, e.addDrop = updateGuard, addDrop
end)

test("microphone denial or hardware failure leaves the Up fallback fully playable", function()
    for _, options in ipairs({ { denied = true }, { startError = true }, { requestError = true }, { readError = true } }) do
        start(3, nil, options)
        enter()
        frame({})
        check(dust.micState == "unavailable" and not dust.listening, "failed microphone did not become unavailable")
        check(e.state == e.STATE_PLAY and dust.active and dust.progress == 0, "microphone failure cancelled or completed the puzzle")
        local requests, starts = mic.requests, mic.starts
        frame({ "a" })
        check(mic.requests == requests and mic.starts == starts, "A repeated a denied or failed microphone request")
        frame({})
        holdUntilClear()
        check(e.tumbler == 2 and h.events().sweetSpot == 1, "Up fallback could not clear dust after microphone failure")
    end
    start(3)
    e.pd.sound.micinput = nil
    enter()
    check(dust.micState == "unavailable", "missing mic API did not select fallback")
    frame({})
    holdUntilClear()
    check(e.tumbler == 2, "missing microphone hardware blocked Up clearing")
end)

test("real microphone frames clear one pin and stop listening before latch audio", function()
    start(3)
    local sweetSpot = e.Sfx.sweetSpot
    e.Sfx.sweetSpot = function()
        check(not dust.listening, "latch sound started while microphone was still listening")
        sweetSpot()
    end
    for spot = 1, 2 do
        enter()
        mic.level = 0.01
        for _ = 1, 32 do frame({}) end
        check(dust.micState == "listening" and dust.progress == 0,
            "new microphone session did not calibrate before clearing")
        mic.level = 0.35
        holdUntilClear({})
        check(e.tumbler == spot + 1 and h.events().sweetSpot == spot and not dust.listening,
            "microphone clearing did not award exactly one stopped-listening latch")
        check(mic.requests == 1 and mic.starts == spot and mic.stops == spot,
            "next pin repeated permission or left microphone open between searches")
        dismiss()
    end
    e.Sfx.sweetSpot = sweetSpot
end)

test("permission dialog elapsed time does not consume run time or guard deadlines", function()
    start(3, { "guard" }, { yieldMs = 7000 })
    local remaining = e.remaining
    e.guardAt, e.guardDeadline = h.advance(0) + 5000, h.advance(0) + 3000
    local nextAt, endAt = e.guardAt, e.guardDeadline
    enter()
    check(mic.requests == 1 and dust.listening, "permission request did not start microphone")
    check(e.remaining == remaining - 20, "permission dialog charged waiting time to countdown")
    check(e.guardAt == nextAt + 7000 and e.guardDeadline == endAt + 7000, "permission yield failed to move guard deadlines")
    frame({})
    check(e.remaining == remaining - 40, "permission yield leaked into the following frame")
end)

test("pause and docking stop the microphone and freeze dust, input and countdown", function()
    for _, mode in ipairs({ "docked", "paused" }) do
        start(3, { "wandering", "one-shot" })
        enter()
        frame({ "a" })
        frame({})
        for _ = 1, 10 do frame({ "up" }) end
        local partial, time, target, clock = dust.progress, e.remaining, e.target, dust.clockMs
        local stops = mic.stops
        if mode == "docked" then h.setDocked(true) else frame({ "b" }) end
        frame({ "down", "up" }, 0, 120)
        frame({}, 0, 120)
        check(not dust.listening and mic.stops == stops + 1, "pause/dock did not stop microphone exactly once")
        check(dust.progress == partial and dust.clockMs == clock and e.remaining == time and e.target == target,
            "pause/dock advanced dust, time, particles or wandering")
        check(e.state ~= e.STATE_LOSE and not h.events().locked, "paused/docked Down reached ONE SHOT")
        if mode == "docked" then h.setDocked(false) else frame({ "b" }) end
        frame({})
        check(e.state == e.STATE_PLAY and dust.active and dust.listening and dust.micState == "calibrating",
            "resume failed to retain partial dust and restart ambient calibration")
        check(dust.progress == partial, "resuming microphone altered prior clearing")
    end
end)

test("clearing and all run endings release the microphone before further sound or input", function()
    for _, ending in ipairs({ "clear", "expiry", "lose", "new-run" }) do
        start(3)
        enter()
        frame({ "a" })
        frame({})
        check(dust.listening, "test microphone did not start")
        local stops = mic.stops
        if ending == "clear" then holdUntilClear()
        elseif ending == "expiry" then e.remaining = 1; frame({ "up", "down" })
        elseif ending == "lose" then e.loseRun("caught")
        else h.start(3, false, {}) end
        check(not dust.listening and mic.stops == stops + 1, "ending did not release microphone once: " .. ending)
        if ending == "clear" then
            check(h.events().sweetSpot == 1 and dust.clearedMs == dust.CLEARED_MS, "clearing omitted real latch or confirmation")
        elseif ending == "expiry" then
            check(e.state == e.STATE_LOSE and e.tumbler == 1 and not h.events().sweetSpot and not h.events().locked,
                "expiry frame awarded a latch or pulled handle")
        elseif ending == "new-run" then
            check(not dust.visible() and not dust.blockOpen and dust.micState == "off" and not dust.wanted,
                "ordinary run inherited microphone permission/input state")
        end
    end
end)

test("timer expiry defeats the final dust-clearing frame", function()
    start(3, { "one-shot" })
    for _ = 1, 2 do clearCurrent(); dismiss() end
    enter()
    frame({})
    dust.progress = 1 - 10 / dust.CLEAR_MS
    e.remaining = 1
    frame({ "up", "down" })
    check(e.state == e.STATE_LOSE and e.loseReason == "timeup" and e.remaining == 0,
        "last clearing frame beat countdown expiry")
    check(e.tumbler == 3 and h.events().sweetSpot == 2 and not h.events().locked,
        "expired final dust frame accepted a real latch or handle")
    check(not dust.visible() and dust.progress == 0 and not dust.listening, "expired final pin retained pending state")
end)

test("system pause, device sleep and termination stop live microphone input", function()
    for _, lifecycle in ipairs({ "system", "sleep", "terminate" }) do
        start(3, { "guard" })
        enter()
        frame({ "a" })
        frame({})
        frame({ "up" })
        local time, progress, stops = e.remaining, dust.progress, mic.stops
        local guardAt, deadline = e.guardAt, h.advance(0) + 3000
        e.guardDeadline = deadline
        if lifecycle == "system" then e.pd.gameWillPause()
        elseif lifecycle == "sleep" then e.pd.deviceWillSleep()
        else e.pd.gameWillTerminate() end
        check(not dust.listening and mic.stops == stops + 1, "lifecycle callback left microphone open: " .. lifecycle)
        h.advance(6000)
        if lifecycle ~= "terminate" then
            if lifecycle == "system" then e.pd.gameWillResume() else e.pd.deviceDidUnlock() end
            check(e.guardAt == guardAt + 6000 and e.guardDeadline == deadline + 6000,
                "system interruption did not preserve hazard deadlines")
            check(e.remaining == time and dust.progress == progress, "system interruption advanced puzzle state")
            frame({})
            check(e.remaining == time - 20 and dust.listening and dust.micState == "calibrating",
                "system resume charged pause time or failed to recalibrate microphone")
        end
    end
end)

test("DUST JAM bans competing inspection bubbles and remains available in legal triples", function()
    check(#e.Mods.list == 13, "catalogue does not contain thirteen implemented modifiers")
    local banned = { blackout = true, nitro = true, decoy = true, keypad = true, ["gear-mesh"] = true, ["too-loud"] = true }
    for id in pairs(banned) do
        check(e.Mods.pairClass("dust-jam", id) == e.Mods.BANNED and e.Mods.pairClass(id, "dust-jam") == e.Mods.BANNED,
            "unsafe dust pair allowed or asymmetric: " .. id)
        check(e.Mods.score({ "dust-jam", id }) == nil, "banned dust pair received playable score")
    end
    for _, id in ipairs({ "spotlight", "scrambled", "four-tumblers", "wandering", "one-shot", "guard" }) do
        check(e.Mods.pairClass("dust-jam", id) ~= e.Mods.BANNED, "useful dust pair was banned: " .. id)
    end
    local saw = false
    for _ = 1, 2000 do
        local mods = assert(e.Mods.roll(3))
        local has = {}
        for _, mod in ipairs(mods) do has[mod.id] = true end
        if has["dust-jam"] then
            saw = true
            for id in pairs(banned) do check(not has[id], "roll included incompatible dust combination: " .. id) end
            check(e.Mods.buildCfg(mods).dustJam, "rolled dust modifier did not enable mechanic")
        end
    end
    check(saw, "DUST JAM never appeared in playable rolls")
    local legal, normal, hard = 0, 0, 0
    for a = 1, #e.Mods.list - 2 do
        for b = a + 1, #e.Mods.list - 1 do
            for c = b + 1, #e.Mods.list do
                local score, mode = e.Mods.score({ e.Mods.list[a], e.Mods.list[b], e.Mods.list[c] })
                if score then
                    legal = legal + 1
                    if mode == "normal" then normal = normal + 1 else hard = hard + 1 end
                end
            end
        end
    end
    check(legal == 134 and normal == 106 and hard == 28, "catalogue triple counts no longer match current compatibility rules")
    print(string.format("Catalogue: %d playable triples (%d normal, %d hard)", legal, normal, hard))
end)

test("SPOTLIGHT reads physical tilt through the real dispatcher without sticky arrow aiming", function()
    local readAccelerometer, isSimulator = e.pd.readAccelerometer, e.pd.isSimulator
    local x = 0.21
    e.pd.readAccelerometer = function() return x, 0, 1 end
    e.pd.isSimulator = false
    start(3, { "spotlight" }, nil, false)
    for _ = 1, 20 do frame({}) end
    check(e.Spotlight.calibrated and near(e.Spotlight.neutralX, 0.21), "real dispatcher did not calibrate physical sensor samples")
    for _ = 1, 20 do frame({ "right" }) end
    check(not e.Spotlight.usingButtons and e.Spotlight.angle == 0, "physical D-pad replaced the accelerometer")
    x = 0.41
    for _ = 1, 20 do frame({ "right" }) end
    check(e.Spotlight.angle > 0 and not e.Spotlight.usingButtons, "held arrow prevented physical tilt from moving the light")
    x = 0.01
    for _ = 1, 20 do frame({}) end
    check(e.Spotlight.angle < 0 and not e.Spotlight.usingButtons, "arrow release left physical aiming stuck in button fallback")
    e.pd.readAccelerometer, e.pd.isSimulator = readAccelerometer, isSimulator
end)

test("simulator aiming yields to hidden KEYPAD and DUST JAM arrow input", function()
    local readAccelerometer, isSimulator = e.pd.readAccelerometer, e.pd.isSimulator
    e.pd.readAccelerometer = function() return 0, 0, 1 end
    for _, simulated in ipairs({ true, false }) do
        e.pd.isSimulator = simulated
        for _, confirmation in ipairs({ "keypad", "dust-jam" }) do
            start(3, { "spotlight", confirmation }, nil, false)
            for _ = 1, 20 do frame({}) end
            for _ = 1, 15 do frame({ "right" }) end
            if simulated then
                check(e.Spotlight.usingButtons and e.Spotlight.angle > 0, "visible simulator inspection could not aim with arrows")
            else
                check(not e.Spotlight.usingButtons and e.Spotlight.angle == 0, "physical arrow overrode the neutral tilt sensor")
            end
            frame({})
            local delta = e.Run.dirs[e.tumbler] * 0.2
            putDial(e.target - delta)
            frame({}, delta)
            check(confirmation == "keypad" and e.Keypad.active or confirmation == "dust-jam" and dust.active,
                "confirmation failed to take over inspection")
            if confirmation == "keypad" then e.Keypad.sequence = { "right", "left", "up", "down" } end
            frame({})
            for _ = 1, 30 do frame({ "right" }) end
            check(not e.Spotlight.usingButtons and e.Spotlight.angle == 0,
                "hidden confirmation arrow made physical tilt sticky: " .. confirmation)
            if confirmation == "keypad" then
                check(e.Keypad.active and e.Keypad.progress == 1, "aiming stole the keypad's right-arrow input")
            else
                check(dust.active and dust.progress == 0, "hidden aiming cleared dust with an unrelated arrow")
            end
        end
    end
    e.pd.readAccelerometer, e.pd.isSimulator = readAccelerometer, isSimulator
end)

test("an unlit SPOTLIGHT pin still earns an ordinary correct-speed latch", function()
    local readAccelerometer, isSimulator = e.pd.readAccelerometer, e.pd.isSimulator
    local x = 0
    e.pd.readAccelerometer = function() return x, 0, 1 end
    e.pd.isSimulator = false
    start(3, { "spotlight" }, nil, false)
    for _ = 1, 20 do frame({}) end
    x = 0.8
    for _ = 1, 30 do frame({}) end
    local delta = e.Run.dirs[e.tumbler] * 0.2
    local _, _, lit = e.Spotlight.pin(e.target, e.target, e.Spotlight.angle)
    check(not lit, "test did not aim the inspection light away from the latch position")
    putDial(e.target - delta)
    frame({}, delta)
    check(e.tumbler == 2 and h.events().sweetSpot == 1 and not dust.visible() and not e.Keypad.active,
        "SPOTLIGHT visibility became an unadvertised condition for a real latch")
    e.pd.readAccelerometer, e.pd.isSimulator = readAccelerometer, isSimulator
end)

test("SPOTLIGHT starts the accelerometer and run exits release it", function()
    local startAccelerometer, stopAccelerometer = e.pd.startAccelerometer, e.pd.stopAccelerometer
    local starts, stops = 0, 0
    e.pd.startAccelerometer = function() starts = starts + 1 end
    e.pd.stopAccelerometer = function() stops = stops + 1 end
    for _, ending in ipairs({ "win", "lose", "ordinary-run", "terminate" }) do
        local beforeStart, beforeStop = starts, stops
        start(3, { "spotlight" }, nil, false)
        check(starts == beforeStart + 1 and stops == beforeStop, "SPOTLIGHT failed to start its sensor")
        if ending == "win" then
            for _ = 1, 3 do h.latch() end
            e.tryHandle()
        elseif ending == "lose" then e.loseRun("caught")
        elseif ending == "ordinary-run" then h.start(3, false, {})
        else e.pd.gameWillTerminate() end
        check(stops == beforeStop + 1, "SPOTLIGHT sensor remained active after " .. ending)
    end
    e.pd.startAccelerometer, e.pd.stopAccelerometer = startAccelerometer, stopAccelerometer
end)

local groups, checks = h.totals()
print(string.format("PASS %d total groups, %d invariant checks", groups, checks))
return h
