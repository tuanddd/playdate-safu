local gfx <const> = playdate.graphics

SpotlightUI = {}

-- The same native bubble as KEYPAD/GEAR MESH: body (28,121), 186x76.
-- Only its 160x48 inspection window contains darkness. HUD and cards stay lit.
local X <const>, Y <const> = 27, 108
local BODY_X <const>, BODY_Y <const> = 1, 13
local W <const>, H <const> = 186, 76
local WINDOW_X <const>, WINDOW_Y <const> = 13, 20
local WINDOW_W <const>, WINDOW_H <const> = 160, 48
local LAMP_X <const>, LAMP_Y <const> = Spotlight.LAMP_X - X - WINDOW_X, Spotlight.LAMP_Y - Y - WINDOW_Y
local RING_X <const>, RING_Y <const> = Spotlight.RING_X - X - WINDOW_X, Spotlight.RING_Y - Y - WINDOW_Y
local CAPTION_Y <const> = 74
local chrome, beams = nil, nil

local function bubbleShape(x, y)
    local points = {}
    local function arc(cx, cy, fromDegrees, toDegrees)
        for i = 0, 4 do
            local radians = math.rad(fromDegrees + (toDegrees - fromDegrees) * i / 4)
            points[#points + 1] = cx + math.cos(radians) * 6
            points[#points + 1] = cy + math.sin(radians) * 6
        end
    end
    arc(x + W, y, 180, 90)
    arc(x + W, y + H, 270, 180)
    arc(x, y + H, 360, 270)
    arc(x, y, 90, 0)
    points[#points + 1], points[#points + 2] = x + 72, y
    points[#points + 1], points[#points + 2] = x + 82, y - 12
    points[#points + 1], points[#points + 2] = x + 95, y
    local shape = playdate.geometry.polygon.new(table.unpack(points))
    shape:close()
    return shape
end

local function bakeChrome(caption)
    local image = gfx.image.new(W + 7, H + BODY_Y + 7)
    gfx.pushContext(image)
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
        gfx.fillRoundRect(WINDOW_X - 1, WINDOW_Y - 1, WINDOW_W + 2, WINDOW_H + 2, 4)
        gfx.setFont(Art.titleFont)
        local inkTop = Art.inkBand(Art.titleFont, Art.CAPS)
        gfx.drawText(caption, BODY_X + math.floor((W - Art.titleFont:getTextWidth(caption)) / 2), CAPTION_Y - inkTop)
    gfx.popContext()
    return image
end

-- A lens-sized base and angular end points form each band. The polygons move,
-- but the Bayer grid is always evaluated at the same local pixel coordinates.
-- Never rotate a finished dither bitmap: that makes its dots crawl on the LCD.
local function beamShape(angle, half)
    local aim, upper, lower = math.rad(angle), math.rad(angle - half), math.rad(angle + half)
    local nx, ny = -math.sin(aim) * 2, math.cos(aim) * 2
    return LAMP_X - nx, LAMP_Y - ny,
        LAMP_X + math.cos(upper) * 155, LAMP_Y + math.sin(upper) * 155,
        LAMP_X + math.cos(lower) * 155, LAMP_Y + math.sin(lower) * 155,
        LAMP_X + nx, LAMP_Y + ny
end

local function drawRing()
    gfx.setLineWidth(2)
    gfx.drawCircleAtPoint(RING_X, RING_Y, 20)
    gfx.setLineWidth(1)
    gfx.drawCircleAtPoint(RING_X, RING_Y, 15)
    gfx.drawCircleAtPoint(RING_X, RING_Y, 4)
    -- Fixed spokes make this read as the underside of the large safe dial.
    gfx.drawLine(RING_X - 11, RING_Y, RING_X - 5, RING_Y)
    gfx.drawLine(RING_X + 5, RING_Y, RING_X + 11, RING_Y)
    gfx.drawLine(RING_X, RING_Y + 5, RING_X, RING_Y + 11)
end

local function drawLamp(angle)
    local a = math.rad(angle)
    local dx, dy, nx, ny = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    local function point(distance, width)
        return LAMP_X + dx * distance + nx * width, LAMP_Y + dy * distance + ny * width
    end
    local x1, y1 = point(-13, -3)
    local x2, y2 = point(-3, -3)
    local x3, y3 = point(-3, 3)
    local x4, y4 = point(-13, 3)
    gfx.setColor(gfx.kColorBlack)
    gfx.fillPolygon(x1, y1, x2, y2, x3, y3, x4, y4)
    gfx.setColor(gfx.kColorWhite)
    gfx.drawPolygon(x1, y1, x2, y2, x3, y3, x4, y4, x1, y1)
    x1, y1 = point(-3, -4)
    x2, y2 = point(0, -4)
    x3, y3 = point(0, 4)
    x4, y4 = point(-3, 4)
    gfx.fillPolygon(x1, y1, x2, y2, x3, y3, x4, y4)
end

local function bakeBeam(angle)
    local image = gfx.image.new(WINDOW_W, WINDOW_H, gfx.kColorBlack)
    local mask = gfx.image.new(WINDOW_W, WINDOW_H, gfx.kColorBlack)
    gfx.pushContext(mask)
        gfx.setColor(gfx.kColorWhite)
        gfx.fillPolygon(beamShape(angle, Spotlight.BEAM_HALF))
    gfx.popContext()
    gfx.pushContext(image)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.setColor(gfx.kColorWhite)
        gfx.setDitherPattern(0.75, gfx.image.kDitherTypeBayer4x4)
        drawRing()
        -- Three nested bands: sparse edge, middle, then a solid bright core.
        -- White setDitherPattern uses transparency in the SDK, hence 1-alpha.
        for _, band in ipairs({ { Spotlight.BEAM_HALF, 0.25 }, { 8, 0.5 }, { 4, 1 } }) do
            gfx.setColor(gfx.kColorWhite)
            gfx.setDitherPattern(1 - band[2], gfx.image.kDitherTypeBayer4x4)
            gfx.fillPolygon(beamShape(angle, band[1]))
        end
        gfx.setStencilImage(mask)
        gfx.setColor(gfx.kColorBlack)
        drawRing()
        gfx.clearStencil()
        -- Twelve o'clock is the catch, so moving the pin toward it is a
        -- meaningful visual hint instead of a disconnected light-chasing toy.
        gfx.setColor(gfx.kColorWhite)
        gfx.fillRect(RING_X - 3, RING_Y - 23, 7, 7)
        gfx.setColor(gfx.kColorBlack)
        gfx.fillRect(RING_X - 1, RING_Y - 23, 3, 4)
        drawLamp(angle)
    gfx.popContext()
    return image
end

local function ensureBaked()
    if chrome then return end
    chrome = {
        ready = bakeChrome("TILT TO AIM"),
        calibrating = bakeChrome("HOLD COMFORTABLY"),
        buttons = bakeChrome("LEFT / RIGHT TO AIM"),
    }
    beams = {}
    for angle = -Spotlight.MAX_ANGLE, Spotlight.MAX_ANGLE, Spotlight.FRAME_STEP do
        beams[#beams + 1] = bakeBeam(angle)
    end
    gfx.setLineWidth(1)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    gfx.setColor(gfx.kColorBlack)
end

-- Immutable chrome and 31 window frames are prepared once, at first run entry.
function SpotlightUI.reset()
    ensureBaked()
end

function SpotlightUI.draw(target, dialPos, aimAngleDegrees, calibrated)
    ensureBaked()
    local angle = math.max(-Spotlight.MAX_ANGLE, math.min(Spotlight.MAX_ANGLE, aimAngleDegrees or Spotlight.angle))
    local frame = math.floor((angle + Spotlight.MAX_ANGLE) / Spotlight.FRAME_STEP + 0.5) + 1
    angle = (frame - 1) * Spotlight.FRAME_STEP - Spotlight.MAX_ANGLE
    if calibrated == nil then calibrated = Spotlight.calibrated end
    local caption = Spotlight.usingButtons and "buttons" or calibrated and "ready" or "calibrating"
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    chrome[caption]:draw(X, Y)
    beams[frame]:draw(X + WINDOW_X, Y + WINDOW_Y)
    local pinX, pinY, lit = Spotlight.pin(target, dialPos, angle)
    if lit then
        pinX, pinY = math.floor(pinX + 0.5), math.floor(pinY + 0.5)
        gfx.setClipRect(X + WINDOW_X, Y + WINDOW_Y, WINDOW_W, WINDOW_H)
        -- Solid 9px pin and a compact glint stay crisp against every band.
        gfx.setColor(gfx.kColorBlack)
        gfx.fillCircleAtPoint(pinX, pinY, 5)
        gfx.setColor(gfx.kColorWhite)
        gfx.fillCircleAtPoint(pinX, pinY, 4)
        gfx.setColor(gfx.kColorBlack)
        gfx.drawLine(pinX - 2, pinY, pinX + 2, pinY)
        gfx.setColor(gfx.kColorWhite)
        gfx.drawLine(pinX + 5, pinY - 5, pinX + 7, pinY - 5)
        gfx.drawLine(pinX + 6, pinY - 6, pinX + 6, pinY - 4)
        gfx.clearClipRect()
    end
    gfx.setLineWidth(1)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    gfx.setColor(gfx.kColorBlack)
end
