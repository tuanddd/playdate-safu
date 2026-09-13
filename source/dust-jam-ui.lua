local gfx <const> = playdate.graphics

DustJamUI = {}

-- The same native-resolution inspection bubble as KEYPAD and GEAR MESH.
-- Body: (28,121)..(214,197); shadow ends at y=201, above the MENU at y=204.
local X <const>, Y <const> = 27, 108
local BODY_X <const>, BODY_Y <const> = 1, 13
local W <const>, H <const> = 186, 76
local CX <const>, CAPTION_Y <const> = 94, 70
local STAGES <const>, PARTICLE_FRAMES <const> = 6, 8
local iconUp <const> = gfx.image.new("images/dpad-up")
local chrome, mechanisms, seated, captions, micImages, particles

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

local function bakeChrome()
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
    gfx.popContext()
    return image
end

local function drawBracket()
    -- Fixed, screwed-on bracket. The spring visibly starts inside it.
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(CX - 25, 18, 50, 8, 2)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillRect(CX - 23, 20, 46, 4)
    gfx.setColor(gfx.kColorBlack)
    for _, x in ipairs({ CX - 20, CX + 20 }) do
        gfx.drawCircleAtPoint(x, 22, 2)
        gfx.drawLine(x - 1, 23, x + 1, 21)
    end
    gfx.fillRect(CX - 7, 23, 15, 3)
end

local function drawReceiver()
    -- A curved metal ledge has a real U-shaped notch under the pin. Coarse
    -- dither belongs to the metal and never moves when dust blows across it.
    local pts = {
        39, 67, 48, 63, 62, 59, 82, 58,
        82, 66, 106, 66, 106, 58, 123, 60, 139, 64, 147, 67,
    }
    local shape = playdate.geometry.polygon.new(table.unpack(pts))
    shape:close()
    gfx.setDitherPattern(0.5, gfx.image.kDitherTypeBayer4x4)
    gfx.fillPolygon(shape)
    gfx.setColor(gfx.kColorBlack)
    gfx.drawPolygon(shape)
    gfx.drawLine(83, 60, 83, 67)
    gfx.drawLine(105, 60, 105, 67)
    gfx.drawLine(83, 67, 105, 67)
end

local function drawPin(drop)
    local top = 36 + drop
    local lastX, lastY = CX, 25
    -- A zigzag spring keeps its endpoints attached at every clearing stage.
    -- The narrow vertical guide inside it makes the pin read as a lock part.
    gfx.setColor(gfx.kColorBlack)
    gfx.drawLine(CX, 25, CX, top)
    for i = 1, 7 do
        local px = CX + (i % 2 == 1 and 7 or -7)
        local py = 25 + math.floor((top - 26) * i / 7 + 0.5)
        gfx.drawLine(lastX, lastY, px, py)
        lastX, lastY = px, py
    end
    gfx.drawLine(lastX, lastY, CX, top + 1)
    gfx.fillRoundRect(CX - 9, top, 19, 19, 3)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillRoundRect(CX - 7, top + 2, 15, 15, 2)
    gfx.setColor(gfx.kColorBlack)
    gfx.drawLine(CX + 4, top + 3, CX + 4, top + 15)
    gfx.drawLine(CX + 6, top + 4, CX + 6, top + 13)
end

-- Each small irregular clump is removed as a unit. Progress therefore reads
-- as an actual dirty mechanism clearing, with no separate meter or spot count.
local dustClumps <const> = {
    { 74, 53, 8, 6 }, { 103, 51, 9, 6 }, { 80, 60, 8, 5 },
    { 99, 59, 9, 6 }, { 86, 56, 8, 7 }, { 92, 60, 7, 6 },
}

local function drawDust(stage)
    gfx.setColor(gfx.kColorBlack)
    for i = stage + 1, STAGES do
        local clump = dustClumps[i]
        local x, y, w, h = clump[1], clump[2], clump[3], clump[4]
        gfx.fillPolygon(x + 2, y, x + w - 2, y + 1, x + w, y + 3,
            x + w - 1, y + h - 1, x + 3, y + h, x, y + h - 2, x, y + 2)
        gfx.setColor(gfx.kColorWhite)
        gfx.fillRect(x + 2, y + 2, 2, 1)
        gfx.fillRect(x + w - 3, y + h - 2, 1, 1)
        gfx.setColor(gfx.kColorBlack)
    end
    if stage < STAGES then
        gfx.fillRect(72, 60, 1, 1)
        gfx.fillRect(111, 58, 1, 1)
        gfx.fillRect(112, 63, 2, 1)
    end
end

local function bakeMechanism(stage, cleared)
    local image = gfx.image.new(W + 1, CAPTION_Y)
    gfx.pushContext(image)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.setLineWidth(1)
        drawReceiver()
        drawBracket()
        drawPin(cleared and 11 or math.min(4, stage))
        if cleared then
            -- A restrained glint belongs to the freed metal, not a HUD tally.
            gfx.drawLine(118, 39, 118, 47)
            gfx.drawLine(114, 43, 122, 43)
            gfx.drawLine(127, 48, 127, 52)
            gfx.drawLine(125, 50, 129, 50)
        else
            drawDust(stage)
        end
    gfx.popContext()
    return image
end

local function bakeCaption(text, withUp)
    local image = gfx.image.new(W + 1, 17)
    gfx.pushContext(image)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.setColor(gfx.kColorBlack)
        local font = Art.titleFont
        local inkTop, inkH = Art.inkBand(font, Art.CAPS)
        local textW = font:getTextWidth(text)
        local width = textW + (withUp and 20 or 0)
        local left = BODY_X + math.floor((W - width) / 2)
        gfx.setFont(font)
        gfx.drawText(text, left, math.floor((16 - inkH) / 2) - inkTop)
        if withUp then iconUp:draw(left + textW + 4, 0) end
    gfx.popContext()
    return image
end

local function drawMic()
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(24, 8, 8, 14, 4)
    gfx.drawLine(21, 16, 21, 21)
    gfx.drawLine(35, 16, 35, 21)
    gfx.drawLine(21, 21, 25, 25)
    gfx.drawLine(35, 21, 31, 25)
    gfx.drawLine(25, 25, 31, 25)
    gfx.fillRect(27, 25, 2, 5)
    gfx.fillRect(23, 30, 10, 2)
end

local function bakeMic(state)
    local image = gfx.image.new(57, 39)
    gfx.pushContext(image)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.setColor(gfx.kColorBlack)
        gfx.setFont(Art.subFont)
        local inkTop = Art.inkBand(Art.subFont, Art.CAPS)
        local function label(text, y)
            gfx.drawText(text, math.floor((57 - Art.subFont:getTextWidth(text)) / 2), y - inkTop)
        end
        if state == "off" or state == "calibrating" then
            label("WAIT...", 15)
        elseif state == "unavailable" then
            iconUp:draw(21, 3)
            label("HOLD", 23)
        else
            drawMic()
        end
    gfx.popContext()
    return image
end

local function bakeParticles(frame)
    local image = gfx.image.new(W + 1, CAPTION_Y)
    gfx.pushContext(image)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.setColor(gfx.kColorBlack)
        -- Eight steps at 80 ms per step. All motion stays clear of the words,
        -- bracket, and mic prompt; only these few escaped dust bits move.
        for i = 0, 4 do
            local age = (frame + i * 2) % PARTICLE_FRAMES
            local px = 112 + age * 5 + i % 2 * 3
            local py = 57 - i * 5 - math.floor(age * (i % 2 + 1) / 3)
            local size = age < 5 and 2 or 1
            gfx.fillRect(px, py, size, size)
            if size == 2 then gfx.fillRect(px + 2, py + 1, 1, 1) end
        end
        -- Air strokes make the active input visible even when HOLD is used.
        local sway = frame % 2
        gfx.drawLine(63, 45 + sway, 70, 43 + sway)
        gfx.drawLine(61, 50, 69, 50)
        gfx.drawLine(64, 55 - sway, 71, 57 - sway)
    gfx.popContext()
    return image
end

local function ensureBaked()
    if chrome then return end
    chrome = bakeChrome()
    mechanisms = {}
    for stage = 0, STAGES do mechanisms[stage + 1] = bakeMechanism(stage, false) end
    seated = bakeMechanism(STAGES, true)
    captions = {
        jammed = bakeCaption("BLOW OR HOLD", true),
        unavailable = bakeCaption("HOLD", true),
        cleared = bakeCaption("K-CHIK!", false),
    }
    micImages = {}
    for _, state in ipairs({ "off", "calibrating", "listening", "unavailable" }) do
        micImages[state] = bakeMic(state)
    end
    particles = {}
    for frame = 0, PARTICLE_FRAMES - 1 do particles[frame + 1] = bakeParticles(frame) end
    gfx.setLineWidth(1)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    gfx.setColor(gfx.kColorBlack)
end

-- Prepare immutable images at run entry, before a sweet spot opens the bubble.
function DustJamUI.reset()
    ensureBaked()
end

-- progress: cleared dust fraction 0..1. phase: "jammed" or "cleared".
-- clockMs is active play time, so pause/docking freeze the particle animation.
-- micState: "off", "calibrating", "listening", or "unavailable".
-- This draw path only selects and blits images; no geometry or text is rebuilt.
function DustJamUI.draw(progress, blowing, phase, clockMs, micState)
    ensureBaked()
    local cleared = phase == "cleared"
    local stage = math.floor(math.max(0, math.min(1, progress or 0)) * STAGES)
    local status = micImages[micState] and micState or "off"
    local mechanism = cleared and seated or mechanisms[stage + 1]
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    chrome:draw(X, Y)
    mechanism:draw(X, Y)
    if not cleared then micImages[status]:draw(X + 11, Y + 25) end
    local caption = cleared and "cleared" or status == "unavailable" and "unavailable" or "jammed"
    captions[caption]:draw(X, Y + CAPTION_Y)
    if blowing and not cleared then
        local frame = math.floor((clockMs or 0) / 80) % PARTICLE_FRAMES + 1
        particles[frame]:draw(X, Y)
    end
    gfx.setLineWidth(1)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    gfx.setColor(gfx.kColorBlack)
end
