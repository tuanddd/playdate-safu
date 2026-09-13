-- A found spot stays pending until its spring pin is free. Only input levels
-- are read; microphone audio is never recorded or saved.
DustJam = {
    CLEAR_MS = 1400,
    CLEARED_MS = 550,
    SETTLE_MS = 220,
    CALIBRATE_MS = 400,
    HOT_MS = 80,
    LEVEL_FLOOR = 0.08,
    NOISE_MARGIN = 0.045,
}

function DustJam.suspend()
    if DustJam.listening then
        playdate.sound.micinput.stopListening()
        DustJam.listening = false
    end
    if Sfx then Sfx.dustListening(false) end
    DustJam.blowing = false
    DustJam.hotMs = 0
end

function DustJam.cancel()
    DustJam.suspend()
    DustJam.active = false
    DustJam.progress = 0
    DustJam.clearedMs = 0
    DustJam.waitForRelease = false
    -- Keep blockOpen through cancellation: an owned Down cannot pull the handle.
end

function DustJam.reset()
    DustJam.cancel()
    DustJam.wanted = false
    DustJam.micState = "off"
    DustJam.blockOpen = false
    DustJam.clockMs = 0
    DustJam.suppressMs = 0
end

function DustJam.listen()
    if not DustJam.active or not DustJam.wanted or DustJam.listening
        or DustJam.micState == "unavailable" then return end
    local mic = playdate.sound and playdate.sound.micinput
    if not mic or not mic.startListening or not mic.getLevel or not mic.stopListening then
        DustJam.micState = "unavailable"
        return
    end
    local ok, started = pcall(mic.startListening, "device")
    if not ok or not started then
        DustJam.micState = "unavailable"
        return
    end
    DustJam.listening = true
    DustJam.micState = "calibrating"
    DustJam.settleMs = DustJam.SETTLE_MS
    DustJam.calMs, DustJam.noiseSum = 0, 0
    DustJam.baseline, DustJam.hotMs = 0, 0
    if Sfx then Sfx.dustListening(true) end
end

-- Called automatically on the first active jam from updatePlay. The SDK
-- permission dialog can yield; the caller rebases deadlines after it returns.
function DustJam.enableMic()
    if not DustJam.active or DustJam.micState ~= "off" then return end
    local mic = playdate.sound and playdate.sound.micinput
    if not mic or not mic.startListening then
        DustJam.micState = "unavailable"
        return
    end
    if mic.requestAccess then
        local ok = pcall(mic.requestAccess, "Blow dust out of the dial. You can also hold Up.")
        if not ok then DustJam.micState = "unavailable"; return end
    end
    DustJam.wanted = true
    DustJam.listen()
end

function DustJam.begin()
    DustJam.active = true
    DustJam.progress, DustJam.clearedMs, DustJam.clockMs = 0, 0, 0
    DustJam.blowing = false
    DustJam.waitForRelease = true
    DustJam.blockOpen = true
    DustJam.listen()
end

function DustJam.visible()
    return DustJam.active or DustJam.clearedMs > 0
end

function DustJam.suppressMic(ms)
    DustJam.suppressMs = math.max(DustJam.suppressMs or 0, ms)
    DustJam.hotMs = 0
end

function DustJam.readLevel()
    if not DustJam.listening then return nil end
    local ok, level = pcall(playdate.sound.micinput.getLevel)
    if not ok or type(level) ~= "number" then
        DustJam.suspend()
        DustJam.micState = "unavailable"
        return nil
    end
    return math.max(0, math.min(1, level))
end

-- Pure input step: synthetic levels use the same calibration and clearing as
-- hardware. Returns true exactly once when the current pin becomes free.
function DustJam.update(dt, upHeld, level)
    DustJam.clockMs = DustJam.clockMs + dt
    DustJam.blowing = false
    DustJam.suppressMs = math.max(0, DustJam.suppressMs - dt)
    if not DustJam.active then
        DustJam.clearedMs = math.max(0, DustJam.clearedMs - dt)
        return false
    end
    if DustJam.waitForRelease and not upHeld then DustJam.waitForRelease = false end
    local air = false
    if level ~= nil and DustJam.listening then
        if DustJam.suppressMs > 0 then
            DustJam.hotMs = 0
        elseif DustJam.settleMs > 0 then
            DustJam.settleMs = math.max(0, DustJam.settleMs - dt)
        elseif DustJam.micState == "calibrating" then
            DustJam.noiseSum = DustJam.noiseSum + level * dt
            DustJam.calMs = DustJam.calMs + dt
            if DustJam.calMs >= DustJam.CALIBRATE_MS then
                DustJam.baseline = DustJam.noiseSum / DustJam.calMs
                DustJam.micState = "listening"
            end
        elseif DustJam.suppressMs <= 0 then
            local threshold = math.max(DustJam.LEVEL_FLOOR,
                DustJam.baseline * 1.8 + DustJam.NOISE_MARGIN)
            if level > threshold then
                DustJam.hotMs = DustJam.hotMs + dt
                air = DustJam.hotMs >= DustJam.HOT_MS
            else
                DustJam.hotMs = 0
                -- Follow a slowly changing quiet room, never learn an active puff.
                DustJam.baseline = DustJam.baseline + (level - DustJam.baseline)
                    * math.min(1, dt / 5000)
            end
        end
    end
    DustJam.blowing = (upHeld and not DustJam.waitForRelease) or air
    if DustJam.blowing then
        DustJam.progress = math.min(1, DustJam.progress + dt / DustJam.CLEAR_MS)
    end
    if DustJam.progress >= 1 then
        DustJam.active = false
        DustJam.clearedMs = DustJam.CLEARED_MS
        DustJam.suspend() -- speaker latch plays only AFTER the mic stops
        return true
    end
    return false
end

DustJam.reset()
