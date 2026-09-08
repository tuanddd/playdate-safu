local gfx <const> = playdate.graphics

-- Native 16px arrows supplied with the game. Keep their pixel grid intact.
KeypadUI = {}
local icons <const> = {
    up = gfx.image.new("images/dpad-up"),
    down = gfx.image.new("images/dpad-down"),
    left = gfx.image.new("images/dpad-left"),
    right = gfx.image.new("images/dpad-right"),
}
KeypadUI.iconDown = icons.down

-- The bubble covers the lower dial. Its upper half, timer, modifier cards,
-- and MENU remain visible; the tip points back to the dial's hub.
local X <const>, Y <const> = 27, 108
local BODY_X <const>, BODY_Y <const> = 1, 13
local W <const>, H <const> = 186, 76
local RAIL_X <const>, RAIL_Y <const>, RAIL_W <const> = 23, 82, 142
local cache = nil
local cachedDirections = {}
local cachedEntered, cachedFailed = nil, nil

-- Same scooped corners and +4px Bayer shadow as Art.drawPlate, with a
-- speech tail built into the polygon so its fill, stroke, and shadow agree.
local function bubbleShape(x, y)
    local pts = {}
    local function arc(cx, cy, fromDeg, toDeg)
        for i = 0, 4 do
            local a = math.rad(fromDeg + (toDeg - fromDeg) * i / 4)
            pts[#pts + 1] = cx + math.cos(a) * 6
            pts[#pts + 1] = cy + math.sin(a) * 6
        end
    end
    arc(x + W, y, 180, 90)
    arc(x + W, y + H, 270, 180)
    arc(x, y + H, 360, 270)
    arc(x, y, 90, 0)
    pts[#pts + 1], pts[#pts + 2] = x + 72, y
    pts[#pts + 1], pts[#pts + 2] = x + 82, y - 12
    pts[#pts + 1], pts[#pts + 2] = x + 95, y
    local shape = playdate.geometry.polygon.new(table.unpack(pts))
    shape:close()
    return shape
end

local function centeredText(text, font, y)
    gfx.setFont(font)
    gfx.drawText(text, BODY_X + math.floor((W - font:getTextWidth(text)) / 2), y)
end

local function rebuild(sequence, entered, failed)
    cache = gfx.image.new(W + 7, H + BODY_Y + 7)
    gfx.pushContext(cache)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.setColor(gfx.kColorBlack)
        gfx.setDitherPattern(0.5, gfx.image.kDitherTypeBayer4x4)
        gfx.fillPolygon(bubbleShape(BODY_X + 4, BODY_Y + 4))
        local shape = bubbleShape(BODY_X, BODY_Y)
        gfx.setColor(gfx.kColorWhite)
        gfx.fillPolygon(shape)
        gfx.setColor(gfx.kColorBlack)
        gfx.setLineWidth(2)
        gfx.drawPolygon(shape)
        gfx.setLineWidth(1)

        centeredText(failed and "TRY AGAIN" or "HOLD THE DIAL", Art.titleFont, 19)

        -- Accepted arrows invert immediately. The next arrow also gets an
        -- underline, so the current step stays clear on a monochrome screen.
        for i = 1, 4 do
            local x = 26 + (i - 1) * 36
            local y = 36
            gfx.setColor(i <= entered and gfx.kColorBlack or gfx.kColorWhite)
            gfx.fillRect(x, y, 28, 24)
            gfx.setColor(gfx.kColorBlack)
            gfx.drawRect(x, y, 28, 24)
            -- Preserve the supplied white center and black outline. Inversion
            -- swaps both colors for accepted arrows without filling the mask.
            gfx.setImageDrawMode(i <= entered and gfx.kDrawModeInverted or gfx.kDrawModeCopy)
            icons[sequence[i]]:draw(x + 6, y + 4)
            gfx.setImageDrawMode(gfx.kDrawModeCopy)
            if i == entered + 1 then gfx.fillRect(x, y + 25, 28, 2) end
            cachedDirections[i] = sequence[i]
        end

        centeredText(failed and "START FROM THE FIRST ARROW" or "PRESS THESE ARROWS", Art.subFont, 64)

        -- End ticks describe the allowed hold range; only the position marker
        -- is dynamic, so crank movement never rebuilds the bubble or its text.
        gfx.setColor(gfx.kColorBlack)
        gfx.drawLine(RAIL_X, RAIL_Y, RAIL_X + RAIL_W, RAIL_Y)
        gfx.drawLine(RAIL_X, RAIL_Y - 3, RAIL_X, RAIL_Y + 3)
        gfx.drawLine(RAIL_X + RAIL_W, RAIL_Y - 3, RAIL_X + RAIL_W, RAIL_Y + 3)
        gfx.drawLine(RAIL_X + RAIL_W / 2, RAIL_Y - 2, RAIL_X + RAIL_W / 2, RAIL_Y + 2)
    gfx.popContext()
    cachedEntered, cachedFailed = entered, failed
end

function KeypadUI.reset()
    cache = nil
    cachedDirections = {}
    cachedEntered, cachedFailed = nil, nil
end

-- sequence: four direction names. entered: number accepted so far (0..3).
-- failed stays true until the next correct input. offsetRatio is dial offset
-- divided by the allowed hold radius, signed -1..1; omit to center the marker.
function KeypadUI.draw(sequence, entered, failed, offsetRatio)
    failed = failed == true
    if not cache or entered ~= cachedEntered or failed ~= cachedFailed
        or sequence[1] ~= cachedDirections[1] or sequence[2] ~= cachedDirections[2]
        or sequence[3] ~= cachedDirections[3] or sequence[4] ~= cachedDirections[4] then
        rebuild(sequence, entered, failed)
    end
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    cache:draw(X, Y)
    local offset = math.max(-1, math.min(1, offsetRatio or 0))
    local markerX = X + RAIL_X + math.floor((offset + 1) * RAIL_W / 2 + 0.5)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillRect(markerX - 3, Y + RAIL_Y - 4, 7, 9)
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRect(markerX - 1, Y + RAIL_Y - 3, 3, 7)
    gfx.setLineWidth(1)
end
