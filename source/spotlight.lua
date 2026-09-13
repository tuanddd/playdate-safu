-- A second way to investigate the dial, never a condition for earning a latch.
-- All timings use active play milliseconds so pause/docking freeze the light.
Spotlight = {
    CALIBRATE_MS = 400,
    SMOOTH_MS = 85,
    DEAD_BAND = 0.018,      -- accelerometer g, relative to a comfortable neutral
    DEGREES_PER_G = 100,
    MAX_ANGLE = 30,        -- degrees above/below a horizontal inspection beam
    FRAME_STEP = 2,
    FRAME_HYSTERESIS = 0.4,
    BUTTON_SPEED = 50,     -- degrees/sec for missing-accelerometer fallback
    BEAM_HALF = 12,        -- widest visible dither band, shared with the UI
    LAMP_X = 60, LAMP_Y = 156,
    RING_X = 132, RING_Y = 153, PIN_RADIUS = 17,
}

local function clamp(value, low, high)
    return math.max(low, math.min(high, value))
end

local function finite(value)
    return type(value) == "number" and value == value
        and value ~= math.huge and value ~= -math.huge
end

-- Quantized output has an extra margin around each old frame: small changes
-- near a 2-degree boundary cannot flicker between two cached dither shapes.
local function selectFrame()
    local half = Spotlight.FRAME_STEP / 2 + Spotlight.FRAME_HYSTERESIS
    if math.abs(Spotlight.smoothAngle - Spotlight.angle) > half then
        Spotlight.angle = clamp(math.floor(Spotlight.smoothAngle / Spotlight.FRAME_STEP + 0.5)
            * Spotlight.FRAME_STEP, -Spotlight.MAX_ANGLE, Spotlight.MAX_ANGLE)
    end
end

function Spotlight.reset()
    Spotlight.angle = 0
    Spotlight.smoothAngle = 0
    Spotlight.manualAngle = 0
    Spotlight.neutralX = 0
    Spotlight.calibrationMs = 0
    Spotlight.calibrationSum = 0
    Spotlight.calibrated = false
    Spotlight.usingButtons = false
end

-- x is the accelerometer's x axis, or nil if unavailable. A missing sensor
-- keeps the inspection usable with left/right; its neutral is never guessed.
-- buttonDirection is -1, 0 or 1. It is ignored while a sensor is available.
function Spotlight.update(dt, x, buttonDirection)
    dt = math.max(0, dt or 0)
    if dt == 0 then return end
    Spotlight.usingButtons = not finite(x)
    local desired = 0
    if Spotlight.usingButtons then
        Spotlight.manualAngle = clamp(Spotlight.manualAngle
            + clamp(buttonDirection or 0, -1, 1) * Spotlight.BUTTON_SPEED * dt / 1000,
            -Spotlight.MAX_ANGLE, Spotlight.MAX_ANGLE)
        desired = Spotlight.manualAngle
    elseif not Spotlight.calibrated then
        local sampleMs = math.min(dt, Spotlight.CALIBRATE_MS - Spotlight.calibrationMs)
        Spotlight.calibrationSum = Spotlight.calibrationSum + x * sampleMs
        Spotlight.calibrationMs = Spotlight.calibrationMs + sampleMs
        Spotlight.neutralX = Spotlight.calibrationSum / Spotlight.calibrationMs
        Spotlight.calibrated = Spotlight.calibrationMs >= Spotlight.CALIBRATE_MS
    else
        local offset = x - Spotlight.neutralX
        local magnitude = math.max(0, math.abs(offset) - Spotlight.DEAD_BAND)
        desired = clamp((offset < 0 and -1 or 1) * magnitude * Spotlight.DEGREES_PER_G,
            -Spotlight.MAX_ANGLE, Spotlight.MAX_ANGLE)
    end
    Spotlight.smoothAngle = Spotlight.smoothAngle + (desired - Spotlight.smoothAngle)
        * (1 - math.exp(-dt / Spotlight.SMOOTH_MS))
    selectFrame()
end

-- Explicit fallback entry point for a simulator/control surface without tilt.
function Spotlight.nudge(dt, direction)
    Spotlight.update(dt, nil, direction)
end

-- Returns screen x/y, whether the pin is lit, and its clockwise degrees from
-- twelve. Zero means the dial is on the target: the pin reaches the top catch.
-- This is a visual clue only. Main's ordinary speed/direction logic owns hits.
function Spotlight.pin(target, dialPos, aimAngleDegrees)
    if target == nil then return nil, nil, false, nil end
    local degrees = ((target - (dialPos or 0)) * 3.6) % 360
    local radians = math.rad(degrees)
    local x = Spotlight.RING_X + math.sin(radians) * Spotlight.PIN_RADIUS
    local y = Spotlight.RING_Y - math.cos(radians) * Spotlight.PIN_RADIUS
    local bearing = math.deg(math.atan((y - Spotlight.LAMP_Y) / (x - Spotlight.LAMP_X)))
    local distance = math.abs(bearing - (aimAngleDegrees or Spotlight.angle))
    return x, y, distance <= Spotlight.BEAM_HALF, degrees
end

Spotlight.reset()
