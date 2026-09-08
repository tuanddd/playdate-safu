-- One active real sweet spot, plus an optional fixed decoy. Future real spots
-- are not placed until needed, so FOUR TUMBLERS never crowds the decoy out.
Spots = { MIN_GAP = 18 }

local function distance(a, b)
    return math.abs(((a - b + 50) % 100) - 50)
end

function Spots.pick(origin, decoy)
    local candidates = {}
    for position = 0, 99 do
        if distance(position, origin) >= Spots.MIN_GAP
            and (decoy == nil or distance(position, decoy) >= Spots.MIN_GAP) then
            candidates[#candidates + 1] = position
        end
    end
    -- Two excluded arcs cannot cover the dial: at least 28 integer positions
    -- remain, even with fractional positions. No retries or silent fallback.
    return candidates[math.random(#candidates)]
end

-- WANDERING reflects at the decoy's clearance boundary. A folded path also
-- handles large time steps without skipping across the forbidden arc.
function Spots.drift(position, decoy, amount, direction)
    if decoy == nil then return (position + amount * direction) % 100, direction end
    local span = 100 - 2 * Spots.MIN_GAP
    local offset = (position - decoy) % 100 - Spots.MIN_GAP
    local phase = direction > 0 and offset or (2 * span - offset)
    phase = (phase + amount) % (2 * span)
    if phase < span then
        return (decoy + Spots.MIN_GAP + phase) % 100, 1
    end
    return (decoy + Spots.MIN_GAP + 2 * span - phase) % 100, -1
end
