-- One visible four-arrow code per real sweet spot. Retrying never rerolls it.
-- Device input and latch effects live in main.lua; this state is plain Lua.
Keypad = {
    LENGTH = 4,
    HOLD_TOL = 4.4, -- dial units either side: twice the entry tolerance
    directions = { "up", "down", "left", "right" },
}

function Keypad.reset()
    Keypad.active = false
    Keypad.sequence = nil
    Keypad.progress = 0
    Keypad.failed = false
    Keypad.waitForRelease = false
    Keypad.blockOpen = false
end

function Keypad.cancel()
    Keypad.active = false
    Keypad.progress = 0
    Keypad.failed = false
    Keypad.waitForRelease = false
    -- Keep the sequence and release gate: a disappearing bubble must never
    -- turn the same Down press into a handle pull, especially with ONE SHOT.
end

function Keypad.newSpot()
    Keypad.cancel()
    Keypad.sequence = {}
    for i = 1, Keypad.LENGTH do
        Keypad.sequence[i] = Keypad.directions[math.random(#Keypad.directions)]
    end
end

function Keypad.begin()
    Keypad.active = true
    Keypad.progress = 0
    Keypad.failed = false
    Keypad.waitForRelease = true
    Keypad.blockOpen = true
end

function Keypad.press(direction)
    if not Keypad.active or Keypad.waitForRelease then return nil end
    if direction ~= Keypad.sequence[Keypad.progress + 1] then
        Keypad.progress = 0
        Keypad.failed = true
        return "wrong"
    end
    Keypad.failed = false
    Keypad.progress = Keypad.progress + 1
    if Keypad.progress == #Keypad.sequence then
        Keypad.active = false
        return "complete"
    end
    return "step"
end

Keypad.reset()
