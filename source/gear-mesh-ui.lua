local gfx <const> = playdate.graphics

GearMeshUI = {}

-- Native 400x240 layout, matching KEYPAD's lower-dial speech bubble. The timer,
-- upper dial, modifier cards, and MENU remain visible throughout the catch.
local X <const>, Y <const> = 27, 108
local BODY_X <const>, BODY_Y <const> = 1, 13
local W <const>, H <const> = 186, 76
local CX <const>, CY <const> = 94, 48
local OUTER_R <const>, ROOT_R <const>, INNER_R <const> = 18, 16, 11
local GAP_HALF <const> = 18
local FRAME_STEP <const>, FRAME_COUNT <const> = 3, 120
local ROTOR_SIZE <const>, ROTOR_CENTER <const> = 41, 20
local CAPTION_Y <const> = 70
local iconDown <const> = gfx.image.new("images/dpad-down")
local chrome, rotors = nil, nil

-- One shared outline for the white body, its stroke, and the +4px Bayer shadow.
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

local function drawCaption(state)
    local text = state == "caught" and "K-CHIK!" or state == "miss" and "NEXT TURN" or "CATCH"
    local font = Art.titleFont
    local inkTop, inkH = Art.inkBand(font, Art.CAPS)
    local textW = font:getTextWidth(text)
    local width = textW + (state == "spinning" and 21 or 0)
    local left = BODY_X + math.floor((W - width) / 2)
    gfx.setFont(font)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    if state == "spinning" then
        iconDown:draw(left, CAPTION_Y)
        left = left + 21
    end
    gfx.drawText(text, left, CAPTION_Y + math.floor((16 - inkH) / 2) - inkTop)
end

local function bakeChrome(state)
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

        -- This top block never rotates: it is the stationary catch the gap
        -- must meet. Its narrow tongue is drawn after the rotor when caught.
        gfx.fillRect(CX - 5, CY - 28, 10, 6)

        if state ~= "caught" then
            -- A clockwise arrow gives the moving gear an immediate direction
            -- cue even in the first still frame of the bubble.
            gfx.setLineWidth(2)
            local prevX, prevY
            for degrees = 44, 132, 11 do
                local a = math.rad(degrees)
                local px, py = CX + math.sin(a) * 29, CY - math.cos(a) * 29
                if prevX then gfx.drawLine(prevX, prevY, px, py) end
                prevX, prevY = px, py
            end
            gfx.fillPolygon(CX + 17, CY + 21, CX + 19, CY + 12, CX + 25, CY + 18)
            gfx.setLineWidth(1)
        end

        drawCaption(state)
    gfx.popContext()
    return image
end

-- A single C-shaped polygon includes both the teeth and the open ring. The
-- 36-degree notch stays completely clear down to the 11px inner radius.
-- Angles are clockwise from 12 o'clock, exactly like GearMesh's catch logic.
local function rotorShape(angle)
    local pts = {}
    local function point(degrees, radius)
        local a = math.rad(angle + degrees)
        pts[#pts + 1] = ROTOR_CENTER + math.sin(a) * radius
        pts[#pts + 1] = ROTOR_CENTER - math.cos(a) * radius
    end

    point(GAP_HALF, ROOT_R)
    for tooth = 1, 18 do
        local start = tooth * 18
        point(start + 3, ROOT_R)
        point(start + 5, OUTER_R)
        point(start + 11, OUTER_R)
        point(start + 13, ROOT_R)
        point(start + 18, ROOT_R)
    end
    for degrees = 360 - GAP_HALF, GAP_HALF, -3 do point(degrees, INNER_R) end
    local shape = playdate.geometry.polygon.new(table.unpack(pts))
    shape:close()
    return shape
end

local function ensureBaked()
    if chrome then return end
    chrome = {
        spinning = bakeChrome("spinning"),
        miss = bakeChrome("miss"),
        caught = bakeChrome("caught"),
    }
    rotors = {}
    for frame = 0, FRAME_COUNT - 1 do
        local image = gfx.image.new(ROTOR_SIZE, ROTOR_SIZE)
        gfx.pushContext(image)
            gfx.setImageDrawMode(gfx.kDrawModeCopy)
            gfx.setColor(gfx.kColorBlack)
            gfx.fillPolygon(rotorShape(frame * FRAME_STEP))
        gfx.popContext()
        rotors[frame + 1] = image
    end
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    gfx.setLineWidth(1)
    gfx.setColor(gfx.kColorBlack)
end

-- Images are immutable and shared across spots/runs. Prepare once at run entry
-- so a player's first sweet spot never pays for text layout or rotor baking.
function GearMeshUI.reset()
    ensureBaked()
end

-- angle: notch center in clockwise degrees from 12 o'clock (zero = aligned).
-- state: "spinning", "miss", or "caught". Caught always seats at exact zero.
function GearMeshUI.draw(angle, state)
    ensureBaked()
    state = chrome[state] and state or "spinning"
    local degrees = state == "caught" and 0 or (angle or 0) % 360
    local frame = math.floor(degrees / FRAME_STEP + 0.5) % FRAME_COUNT + 1
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    chrome[state]:draw(X, Y)
    rotors[frame]:draw(X + CX - ROTOR_CENTER, Y + CY - ROTOR_CENTER)
    gfx.setColor(gfx.kColorBlack)
    if state == "caught" then
        -- Fits inside the notch's narrow inner end, visibly meshing the fixed
        -- catch with the gear. Draw last so the tongue remains solid.
        gfx.fillRect(X + CX - 2, Y + CY - 23, 5, 13)
    end
    gfx.setLineWidth(1)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
end
