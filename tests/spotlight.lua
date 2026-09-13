-- Run from the repository root: luajit tests/spotlight.lua
-- Exercise real tilt/filter geometry without a renderer or hardware stubs.
dofile("source/spotlight.lua")
local groups, checks = 0, 0
local function check(value, message)
    checks = checks + 1
    assert(value, message)
end
local function test(name, fn)
    fn()
    groups = groups + 1
    print("PASS " .. name)
end
local function close(a, b) return math.abs(a - b) < 0.000001 end
local function calibrate(neutral)
    Spotlight.reset()
    for _ = 1, 20 do Spotlight.update(20, neutral or 0) end
end

test("comfortable neutral is duration-weighted and held during calibration", function()
    Spotlight.reset()
    Spotlight.update(100, 0.2)
    Spotlight.update(200, 0.3)
    Spotlight.update(80, 0.25)
    check(not Spotlight.calibrated and Spotlight.angle == 0, "light moved or finished before 400 ms")
    Spotlight.update(20, 0.25)
    check(Spotlight.calibrated and close(Spotlight.neutralX, 0.2625), "neutral did not weight elapsed samples")
    Spotlight.update(100, Spotlight.neutralX)
    check(Spotlight.angle == 0, "comfortable neutral failed to center beam")
end)

test("tilt smoothing is time-based, deadband is quiet, and travel is bounded", function()
    local values = {}
    for index, steps in ipairs({ { 200 }, { 100, 100 }, { 20, 20, 60, 40, 60 } }) do
        calibrate(0.2)
        for _, dt in ipairs(steps) do Spotlight.update(dt, 0.4) end
        values[index] = Spotlight.smoothAngle
    end
    check(close(values[1], values[2]) and close(values[2], values[3]), "filter depends on frame partition")
    calibrate(0.3)
    for _ = 1, 100 do Spotlight.update(20, 0.3 + math.sin(_) * Spotlight.DEAD_BAND) end
    check(Spotlight.angle == 0, "hand tremor escaped deadband")
    Spotlight.update(1000, 100)
    check(Spotlight.angle == 30, "positive tilt did not clamp to final cached frame")
    Spotlight.update(1000, -100)
    check(Spotlight.angle == -30, "negative tilt did not clamp to first cached frame")
end)

test("cached-frame hysteresis prevents repeated boundary flickering", function()
    calibrate()
    Spotlight.smoothAngle, Spotlight.angle = 1.2, 0
    Spotlight.update(1, Spotlight.DEAD_BAND + 0.012)
    check(Spotlight.angle == 0, "small boundary excursion switched frames")
    Spotlight.smoothAngle = 1.5
    Spotlight.update(1, Spotlight.DEAD_BAND + 0.015)
    check(Spotlight.angle == 2, "intentional travel did not switch frames")
    Spotlight.smoothAngle = 0.8
    Spotlight.update(1, Spotlight.DEAD_BAND + 0.008)
    check(Spotlight.angle == 2, "return over nominal boundary flickered backwards")
end)

test("missing or invalid accelerometer has a usable bounded button fallback", function()
    Spotlight.reset()
    Spotlight.update(400, nil, 1)
    check(Spotlight.usingButtons and Spotlight.angle > 0, "missing sensor did not enable buttons")
    Spotlight.update(1000, 0 / 0, -1)
    check(Spotlight.usingButtons and Spotlight.angle == -30, "invalid sample failed to use bounded fallback")
    local angle = Spotlight.angle
    Spotlight.update(0, nil, 1)
    check(Spotlight.angle == angle, "zero active time moved fallback")
    Spotlight.update(400, 0.1, 1)
    check(Spotlight.calibrated and not Spotlight.usingButtons and close(Spotlight.neutralX, 0.1), "sensor recovery did not calibrate")
    Spotlight.update(1000, 0.1, 1)
    check(Spotlight.angle == 0, "fallback buttons fought live tilt input")
end)

test("pin follows the dial continuously and reaches twelve on the sweet spot", function()
    for _, target in ipairs({ 0, 1, 49.5, 99, 125 }) do
        local x, y, _, angle = Spotlight.pin(target, target)
        check(close(x, Spotlight.RING_X) and close(y, Spotlight.RING_Y - Spotlight.PIN_RADIUS)
            and close(angle, 0), "target failed to arrive at fixed top catch")
        local quarterX, quarterY = Spotlight.pin(target, target - 25)
        check(close(quarterX, Spotlight.RING_X + Spotlight.PIN_RADIUS)
            and close(quarterY, Spotlight.RING_Y), "quarter turn used the wrong mapping")
    end
    local x1, y1 = Spotlight.pin(1, 99)
    local x2, y2 = Spotlight.pin(101, -1)
    check(close(x1, x2) and close(y1, y2), "wrapping changed pin geometry")
    local x, y, lit = Spotlight.pin(nil, 0)
    check(x == nil and y == nil and not lit, "finished target leaked a pin")
end)

test("every ring position can be lit and hidden using real cached beam angles", function()
    for dial = 0, 99.5, 0.5 do
        local saw, hidden = false, false
        for aim = -Spotlight.MAX_ANGLE, Spotlight.MAX_ANGLE, Spotlight.FRAME_STEP do
            local x, y, lit = Spotlight.pin(0, dial, aim)
            saw = saw or lit
            hidden = hidden or not lit
            check(x >= 40 + 5 and x <= 200 - 5 and y >= 128 + 5 and y <= 176 - 5,
                "pin is clipped by the native inspection window")
        end
        check(saw, "some pin positions cannot be illuminated")
        check(hidden, "some pin positions are always revealed")
    end
end)

test("new runs clear calibration, aim and fallback state", function()
    calibrate(0.4)
    Spotlight.nudge(1000, 1)
    Spotlight.reset()
    check(Spotlight.angle == 0 and Spotlight.smoothAngle == 0 and Spotlight.manualAngle == 0,
        "new run inherited aim")
    check(not Spotlight.calibrated and not Spotlight.usingButtons and Spotlight.calibrationMs == 0,
        "new run inherited sensor calibration")
end)

print(string.format("PASS %d SPOTLIGHT groups, %d checks", groups, checks))
