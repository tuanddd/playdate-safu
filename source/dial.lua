local gfx <const> = playdate.graphics

Art = {}

Art.numFont = gfx.font.new("fonts/Nontendo-Bold")
Art.sfxFont = gfx.font.new("fonts/Bouncy-30")
Art.timerFont = gfx.font.new("fonts/Asheville-Mono-Light-24-px")
Art.uiFont = gfx.font.new("fonts/Roobert-11-Medium")

Art.iconClock = gfx.image.new("images/clock")
Art.iconA = gfx.image.new("images/btn-a")
Art.iconB = gfx.image.new("images/btn-b")

local FADES <const> = { 0.80, 0.60, 0.42, 0.26, 0.12 }
local WIGGLE <const> = { 13, -10, 7, -4, 2, 0 }

local numImages = {}

local function makeNumberImage(text)
    gfx.setFont(Art.numFont)
    local w, h = gfx.getTextSize(text)
    local img = gfx.image.new(w + 2, h + 2)
    gfx.pushContext(img)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.drawText(text, 1, 1)
    gfx.popContext()
    return img
end

for n = 0, 90, 10 do
    numImages[n] = makeNumberImage(string.format("%02d", n))
end

local function outlinedText(font, text, ring)
    gfx.setFont(font)
    local w, h = gfx.getTextSize(text)
    local pad = ring + 2
    local img = gfx.image.new(w + pad * 2, h + pad * 2)
    gfx.pushContext(img)
        gfx.setImageDrawMode(gfx.kDrawModeFillBlack)
        for dx = -ring, ring do
            for dy = -ring, ring do
                if dx * dx + dy * dy <= ring * ring + 1 then
                    gfx.drawText(text, pad + dx, pad + dy)
                end
            end
        end
        gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
        gfx.drawText(text, pad, pad)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
    gfx.popContext()
    return img
end

local function bake(img, angle, scale)
    local w, h = img:getSize()
    local rad = math.rad(math.abs(angle))
    local sn, cs = math.sin(rad), math.cos(rad)
    local nw = math.ceil((w * cs + h * sn) * scale) + 4
    local nh = math.ceil((w * sn + h * cs) * scale) + 4
    local out = gfx.image.new(nw, nh)
    gfx.pushContext(out)
        img:drawRotated(nw / 2, nh / 2, angle, scale)
    gfx.popContext()
    return { img = out, hw = nw / 2, hh = nh / 2 }
end

local function frameOf(img)
    local w, h = img:getSize()
    return { img = img, hw = w / 2, hh = h / 2 }
end

function Art.makeSfx(text, scale, wiggle)
    local src = outlinedText(Art.sfxFont, text, 3)
    local set = { frames = {}, fades = {} }
    if wiggle == false then
        set.frames[1] = bake(src, 0, scale)
    else
        for i, ang in ipairs(WIGGLE) do
            set.frames[i] = bake(src, ang, scale)
        end
    end
    local final = set.frames[#set.frames]
    set.hw, set.hh = final.hw, final.hh
    for i, a in ipairs(FADES) do
        set.fades[i] = frameOf(final.img:fadedImage(a, gfx.image.kDitherTypeBayer4x4))
    end
    return set
end

function Art.makeTiny(text)
    local src = outlinedText(Art.numFont, text, 1)
    local set = { frames = { frameOf(src) }, fades = {} }
    set.hw, set.hh = set.frames[1].hw, set.frames[1].hh
    for i, a in ipairs(FADES) do
        set.fades[i] = frameOf(src:fadedImage(a, gfx.image.kDitherTypeBayer4x4))
    end
    return set
end

function Art.drawDial(cx, cy, r, pos)
    local rim = math.floor(r * 0.12) + 2
    local hub = math.floor(r * 0.30)
    local nr = r - math.floor(r * 0.36)

    gfx.setColor(gfx.kColorBlack)
    gfx.fillCircleAtPoint(cx, cy, r + rim)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillCircleAtPoint(cx, cy, r)

    gfx.setColor(gfx.kColorWhite)
    gfx.setLineWidth(2)
    for n = 0, 99, 2 do
        local a = math.rad((pos - n) * 3.6)
        local sa, ca = math.sin(a), math.cos(a)
        gfx.drawLine(cx + sa * (r + 2), cy - ca * (r + 2), cx + sa * (r + rim - 1), cy - ca * (r + rim - 1))
    end

    gfx.setColor(gfx.kColorBlack)
    for n = 0, 99 do
        local a = math.rad((pos - n) * 3.6)
        local sa, ca = math.sin(a), math.cos(a)
        local inner
        if n % 10 == 0 then
            gfx.setLineWidth(3)
            inner = r - r * 0.20
        elseif n % 5 == 0 then
            gfx.setLineWidth(2)
            inner = r - r * 0.15
        else
            gfx.setLineWidth(1)
            inner = r - r * 0.09
        end
        gfx.drawLine(cx + sa * (r - 2), cy - ca * (r - 2), cx + sa * inner, cy - ca * inner)
    end
    gfx.setLineWidth(1)

    for n = 0, 90, 10 do
        local ang = (pos - n) * 3.6
        local a = math.rad(ang)
        numImages[n]:drawRotated(cx + math.sin(a) * nr, cy - math.cos(a) * nr, ang)
    end

    gfx.setColor(gfx.kColorBlack)
    gfx.fillCircleAtPoint(cx, cy, hub)
    gfx.setColor(gfx.kColorWhite)
    gfx.setLineWidth(3)
    for i = 0, 3 do
        local a = math.rad(pos * 3.6 + i * 90)
        local sa, ca = math.sin(a), math.cos(a)
        gfx.drawLine(cx + sa * hub * 0.35, cy - ca * hub * 0.35, cx + sa * hub * 0.86, cy - ca * hub * 0.86)
    end
    gfx.setLineWidth(1)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillCircleAtPoint(cx, cy, math.max(3, hub * 0.25))
    gfx.setColor(gfx.kColorBlack)
    gfx.fillCircleAtPoint(cx, cy, math.max(2, hub * 0.13))
end

function Art.drawDots(cx, y, filled, light)
    local bg = light and gfx.kColorBlack or gfx.kColorWhite
    local fg = light and gfx.kColorWhite or gfx.kColorBlack
    for i = 1, 3 do
        local x = cx + (i - 2) * 28
        gfx.setColor(bg)
        gfx.fillCircleAtPoint(x, y, 9)
        gfx.setColor(fg)
        gfx.setLineWidth(2)
        gfx.drawCircleAtPoint(x, y, 8)
        if i <= filled then
            gfx.fillCircleAtPoint(x, y, 5)
        end
    end
    gfx.setLineWidth(1)
    gfx.setColor(gfx.kColorBlack)
end
