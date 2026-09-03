local gfx <const> = playdate.graphics

Art = {}

-- Roobert throughout, with Bouncy-30 reserved for the manga SFX.
-- NOTE: the SDK has no Roobert Medium below 11px — 10px exists only in Bold, and
-- the "Halved" cuts measure identically to their parents. So the small UI face is
-- Roobert-10-Bold; the only non-mono alternative at that size does not exist.
Art.uiFont = gfx.font.new("fonts/Roobert-11-Medium")   -- headings, pause menu
Art.numFont = gfx.font.new("fonts/Roobert-10-Bold")    -- HUD timer, Ⓐ/Ⓑ prompts
-- The modifier cards are the one place Roobert cannot serve: it has no Light
-- at any size and no Medium under 11px, so two weights at a size small enough
-- for a 58px card do not exist in the family. Nontendo has Bold and Light at the
-- same 13px line box, which is what lets the cards carry a full sentence.
Art.titleFont = gfx.font.new("fonts/Nontendo-Bold")    -- card + catalogue titles
Art.subFont = gfx.font.new("fonts/Nontendo-Light")     -- card + catalogue subtitles
Art.dialFont = gfx.font.new("fonts/Roobert-10-Bold")   -- dial numerals
Art.sfxFont = gfx.font.new("fonts/Bouncy-30")          -- manga SFX
Art.timerFont = gfx.font.new("fonts/Roobert-20-Medium")-- win panel readout

Art.iconClock14 = gfx.image.new("images/clock-14")
Art.iconHand = gfx.image.new("images/hand-cursor")
Art.iconA = gfx.image.new("images/btn-a-14")
Art.iconB = gfx.image.new("images/btn-b-14")

local FADES <const> = { 0.80, 0.60, 0.42, 0.26, 0.12 }
local WIGGLE <const> = { 13, -10, 7, -4, 2, 0 }

local numImages = {}

local function makeNumberImage(text)
    gfx.setFont(Art.dialFont)
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

function Art.drawDots(cx, y, filled, light, count)
    count = count or 3
    local bg = light and gfx.kColorBlack or gfx.kColorWhite
    local fg = light and gfx.kColorWhite or gfx.kColorBlack
    for i = 1, count do
        local x = cx + (i - (count + 1) / 2) * 28
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

-- Canonical samples: caps with no space, no descender and no punctuation, so
-- every label of a given font aligns identically instead of shifting with its
-- own letters. CAPS covers the uppercase UI text; DIGITS the timer.
Art.CAPS = "ABEHOX"
Art.DIGITS = "0123456789"

-- A bitmap font's glyphs do not fill its line box — there is slack above the
-- caps and below the baseline for descenders. Centring a label by its line
-- height therefore leaves it sitting high next to a glyph that fills its box.
-- Measure where the ink actually starts and how tall it is, once per font.
local inkCache = {}

function Art.inkBand(font, sample)
    local key = tostring(font) .. "\0" .. sample
    local hit = inkCache[key]
    if hit then return hit[1], hit[2] end

    -- Measure through the font's own methods: gfx.getTextSize's second argument
    -- is a font *family* table, not a font, and passing one gives a 0-width box.
    local w = font:getTextWidth(sample)
    local h = font:getHeight()
    local probe = gfx.image.new(w + 2, h + 4, gfx.kColorWhite)
    gfx.pushContext(probe)
        -- pushContext does not reset the image draw mode: if a caller left
        -- FillWhite set, the probe would draw white on white and measure nothing.
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        gfx.setColor(gfx.kColorBlack)
        gfx.setFont(font)
        gfx.drawText(sample, 0, 0)
    gfx.popContext()
    gfx.setImageDrawMode(gfx.kDrawModeCopy)

    local top, bottom
    for y = 0, h + 3 do
        for x = 0, w + 1 do
            if probe:sample(x, y) == gfx.kColorBlack then
                if not top then top = y end
                bottom = y
                break
            end
        end
    end
    top = top or 0
    bottom = bottom or (h - 1)
    inkCache[key] = { top, bottom - top + 1 }
    return top, bottom - top + 1
end

-- ---------------------------------------------------------------------------
-- Play-screen furniture: the vault door, the recessed dial well, the timer
-- plate and the modifier cards. Layout mirrors images/hud-01-vault-door.png.
-- Drawing only — Art knows nothing about what a modifier does.

local CARD_NOTCH <const> = 6

-- The card outline as a closed polygon: a rectangle whose four corners are
-- scooped inward by a quarter circle centred ON the corner. Returned as a
-- geometry.polygon so the fill, the shadow and the stroke are all the same
-- shape — the shadow follows the scoops instead of squaring them off.
local function notchedPoly(x, y, w, h, r)
    local pts = {}
    local function arc(cx, cy, fromDeg, toDeg)
        for i = 0, 4 do
            local a = math.rad(fromDeg + (toDeg - fromDeg) * i / 4)
            pts[#pts + 1] = cx + math.cos(a) * r
            pts[#pts + 1] = cy + math.sin(a) * r
        end
    end
    arc(x + w, y, 180, 90)          -- top-right scoop
    arc(x + w, y + h, 270, 180)     -- bottom-right
    arc(x, y + h, 360, 270)         -- bottom-left
    arc(x, y, 90, 0)                -- top-left
    local poly = playdate.geometry.polygon.new(table.unpack(pts))
    poly:close()
    return poly
end

-- Black surround, white door plate, engraved inner frame, rivets.
function Art.drawDoor()
    gfx.clear(gfx.kColorBlack)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillRect(3, 3, 394, 234)
    gfx.setColor(gfx.kColorBlack)
    gfx.setLineWidth(2)
    gfx.drawRect(4, 4, 392, 232)
    gfx.drawRect(8, 8, 384, 224)
    gfx.setLineWidth(1)
    for i = 0, 12 do
        local x = 28 + i * 28
        gfx.fillRect(x - 2, 14, 4, 4)
        gfx.fillRect(x - 2, 222, 4, 4)
    end
    for i = 0, 5 do
        local y = 44 + i * 29
        gfx.fillRect(14, y - 2, 4, 4)
        gfx.fillRect(382, y - 2, 4, 4)
    end
end

-- The dial sits in a shallow dithered recess.
function Art.drawDialWell(cx, cy, r)
    gfx.setColor(gfx.kColorBlack)
    gfx.setDitherPattern(0.25, gfx.image.kDitherTypeBayer4x4)
    gfx.fillCircleAtPoint(cx, cy, r)
    gfx.setColor(gfx.kColorBlack)
    gfx.setLineWidth(2)
    gfx.drawCircleAtPoint(cx, cy, r)
    gfx.setLineWidth(1)
end

-- Timer readout on a black plate over a checkered offset shadow. The plate is
-- sized from a fixed reference string, not the live text, so it cannot twitch
-- as the digits change. Icon and text are both centred on the plate's midline.
local TIMER_REF <const> = "00:00.00"

-- The plate chrome only: black plate, checkered offset shadow, clock glyph.
-- Static for the whole run, so it can be baked into the background image.
-- Returns where the digits go, and the plate size.
function Art.drawTimerPlate(x, y)
    local rw = Art.numFont:getTextWidth(TIMER_REF)
    local h = math.max(24, Art.numFont:getHeight() + 8)
    local w = 6 + 14 + 6 + rw + 8
    gfx.setColor(gfx.kColorBlack)
    gfx.setDitherPattern(0.5, gfx.image.kDitherTypeBayer4x4)
    gfx.fillRoundRect(x + 4, y + 4, w, h, 4)
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(x, y, w, h, 4)
    gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    Art.iconClock14:draw(x + 6, y + math.floor((h - 14) / 2))
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    local inkTop, inkH = Art.inkBand(Art.numFont, Art.DIGITS)
    return x + 26, y + math.floor((h - inkH) / 2) - inkTop, w, h
end

-- The digits, redrawn every frame over the baked plate.
function Art.drawTimerText(tx, ty, text)
    gfx.setFont(Art.numFont)
    gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    gfx.drawText(text, tx, ty)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
end

-- One modifier plate: scooped corners over a checkered offset shadow, then two
-- rows — [icon | title] with the icon centred on the title, subtitle beneath at
-- the title's x. `icon` is a 14x14 image or nil.
-- A white plate with scooped corners over a checkered shadow offset down-right.
-- Used by the modifier cards and by the pause menu, so they read as one family.
function Art.drawPlate(x, y, w, h)
    local n <const> = CARD_NOTCH
    gfx.setColor(gfx.kColorBlack)
    gfx.setDitherPattern(0.5, gfx.image.kDitherTypeBayer4x4)
    gfx.fillPolygon(notchedPoly(x + 4, y + 4, w, h, n))
    local shape = notchedPoly(x, y, w, h, n)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillPolygon(shape)
    gfx.setColor(gfx.kColorBlack)
    gfx.setLineWidth(2)
    gfx.drawPolygon(shape)
    gfx.setLineWidth(1)
end

-- Square-cornered plate for the pause menu — same checkered shadow, no scoops.
function Art.drawPanel(x, y, w, h)
    gfx.setColor(gfx.kColorBlack)
    gfx.setDitherPattern(0.5, gfx.image.kDitherTypeBayer4x4)
    gfx.fillRect(x + 4, y + 4, w, h)
    gfx.setColor(gfx.kColorWhite)
    gfx.fillRect(x, y, w, h)
    gfx.setColor(gfx.kColorBlack)
    gfx.setLineWidth(2)
    gfx.drawRect(x, y, w, h)
    gfx.setLineWidth(1)
end

function Art.drawModCard(x, y, w, h, icon, title, sub)
    Art.drawPlate(x, y, w, h)

    -- Row 1 is [icon | title], the 14x14 icon drawn 1:1 and centred against the
    -- title's line. Row 2 is the subtitle, one size down, wrapped to 2 lines.
    local ICON <const> = 14
    local textX = x + 9 + ICON + 6
    local availW = w - (textX - x) - 6

    gfx.setFont(Art.titleFont)
    local _, th = gfx.getTextSize(title)
    gfx.setFont(Art.subFont)
    local _, lineH = gfx.getTextSize("Xy")
    local _, sh = gfx.getTextSizeForMaxWidth(sub, availW)
    if sh > lineH * 2 then sh = lineH * 2 end

    local top = y + math.floor((h - (th + 3 + sh)) / 2)
    local inkTop, inkH = Art.inkBand(Art.titleFont, Art.CAPS)
    if icon then icon:draw(x + 9, top + inkTop + math.floor((inkH - ICON) / 2)) end
    gfx.setFont(Art.titleFont)
    gfx.drawText(title, textX, top)

    gfx.setFont(Art.subFont)
    gfx.drawTextInRect(sub, textX, top + th + 3, availW, lineH * 2)
end

-- ---------------------------------------------------------------------------
-- Modifier visuals.

-- BLACKOUT's flashlight, shining up from below the bottom edge.
--
-- Drawn as a handful of nested wedges of decreasing dither density rather than a
-- per-pixel falloff: 400x240 is 96k Lua iterations, which costs a visible pause
-- at run start, and at 1-bit a stepped ramp is indistinguishable from a smooth
-- one. White here means "lit" - the caller uses this as a stencil.
-- Two passes, because the beam and the things it lights need different curves.
--
-- BEAM is the light itself hanging in the dark air, sparse enough to read as
-- haze. MASK is the falloff applied to the cards: its floor stays high, because
-- a card dithered below about 70% loses its black text against the black room,
-- and which modifiers are active is information the player cannot do without.
local BEAM_BANDS <const> = {
    { r = 350, a = 0.12 },
    { r = 272, a = 0.20 },
    { r = 198, a = 0.30 },
    { r = 130, a = 0.42 },
}
local MASK_BANDS <const> = {
    { r = 350, a = 0.80 },
    { r = 255, a = 0.90 },
    { r = 168, a = 0.97 },
    { r = 96,  a = 1.00 },
}

local function wedge(fx, fy, r, half, steps)
    local p = { fx, fy }
    local a0 = -math.pi / 2 - half
    for i = 0, steps do
        local a = a0 + (2 * half) * i / steps
        p[#p + 1] = fx + math.cos(a) * r
        p[#p + 1] = fy + math.sin(a) * r
    end
    return p
end

local function cone(fx, fy, half, bands)
    for _, b in ipairs(bands) do
        -- setColor must be re-set inside the loop: setDitherPattern resets the
        -- draw colour to black, so hoisting this out paints every band after the
        -- first in black and eats the ones before it.
        gfx.setColor(gfx.kColorWhite)
        -- setDitherPattern's argument is TRANSPARENCY, not coverage: 0.1 is
        -- nearly solid, 0.9 nearly invisible. Verified on a swatch, because
        -- getting this backwards silently inverts the whole falloff.
        gfx.setDitherPattern(1 - b.a, gfx.image.kDitherTypeBayer4x4)
        gfx.fillPolygon(table.unpack(wedge(fx, fy, b.r, half, 14)))
    end
    gfx.setColor(gfx.kColorWhite)
end

-- The visible beam, drawn straight onto the dark room.
function Art.drawLightBeam(fx, fy, half)
    cone(fx, fy, half or 0.62, BEAM_BANDS)
end

-- The same cone as a stencil for whatever the beam falls on.
function Art.drawLightMask(fx, fy, half)
    cone(fx, fy, half or 0.62, MASK_BANDS)
end

-- TOO LOUD's music note, baked once with the `// \\` emphasis strokes either
-- side that say "this is loud". Black on transparent, to read on the white door.
function Art.makeNoteBurst(icon)
    local w, h = 46, 20
    local img = gfx.image.new(w, h)
    gfx.pushContext(img)
        gfx.setColor(gfx.kColorBlack)
        gfx.setLineWidth(2)
        -- // on the left, \\ on the right
        gfx.drawLine(3, 14, 8, 4)
        gfx.drawLine(8, 14, 13, 4)
        gfx.drawLine(w - 3, 14, w - 8, 4)
        gfx.drawLine(w - 8, 14, w - 13, 4)
        gfx.setLineWidth(1)
        if icon then icon:draw((w - 14) // 2, 3) end
    gfx.popContext()
    return { img = img, hw = w / 2, hh = h / 2 }
end

-- GUARD's sound marks: the manga `// \\\\` with no glyph between them, meaning
-- only "something made a noise over there". Built as a full SFX set so it
-- wiggles in and dithers out exactly like K-CHIK and TOO FAST do.
--
-- It is not a telegraph and does not lift the TOO LOUD + GUARD ban: it says a
-- sound happened, not that it was footsteps, and carries none of the three-second
-- deadline that actually decides the run.
function Art.makeMarks(scale)
    local w, h <const> = 40, 26
    local src = gfx.image.new(w, h)
    gfx.pushContext(src)
        -- black first and fat, white over it thin: the same read as outlinedText
        for _, pass in ipairs({ { gfx.kColorBlack, 7 }, { gfx.kColorWhite, 3 } }) do
            gfx.setColor(pass[1])
            gfx.setLineWidth(pass[2])
            gfx.drawLine(6, 20, 12, 6)
            gfx.drawLine(13, 20, 19, 6)
            gfx.drawLine(w - 6, 20, w - 12, 6)
            gfx.drawLine(w - 13, 20, w - 19, 6)
        end
        gfx.setLineWidth(1)
    gfx.popContext()

    local set = { frames = {}, fades = {} }
    for i, ang in ipairs(WIGGLE) do set.frames[i] = bake(src, ang, scale or 1.2) end
    local final = set.frames[#set.frames]
    set.hw, set.hh = final.hw, final.hh
    for i, a in ipairs(FADES) do
        set.fades[i] = frameOf(final.img:fadedImage(a, gfx.image.kDitherTypeBayer4x4))
    end
    return set
end

-- NITRO's spirit level, drawn over everything else. The surface stays level
-- while the door tilts under it, so the player reads their own hands rather than
-- a number. Dithered so the dial and cards stay legible underneath.
--
-- `angle` is radians of surface tilt, `danger` 0..1 how close to spilling.
function Art.drawWaterLayer(angle, danger)
    -- Sits low enough to leave the modifier cards and the Ⓐ/Ⓑ prompts readable.
    -- It is a hazard overlay, not a curtain: covering the card column would hide
    -- which modifiers are running.
    local cx, cy <const> = 200, 210
    local dx = math.cos(angle) * 300
    local dy = math.sin(angle) * 300
    -- the surface, extended past both edges, closed off the bottom of the screen
    local poly = {
        cx - dx, cy - dy,
        cx + dx, cy + dy,
        cx + dx, 260,
        cx - dx, 260,
    }
    gfx.setColor(gfx.kColorBlack)
    -- transparency, so higher is sparser; it thickens as you near spilling
    gfx.setDitherPattern(danger > 0.75 and 0.52 or 0.72, gfx.image.kDitherTypeBayer4x4)
    gfx.fillPolygon(table.unpack(poly))
    -- the waterline itself stays solid, so the horizon is always readable
    gfx.setColor(gfx.kColorBlack)
    gfx.setLineWidth(danger > 0.75 and 3 or 2)
    gfx.drawLine(cx - dx, cy - dy, cx + dx, cy + dy)
    gfx.setLineWidth(1)
end
