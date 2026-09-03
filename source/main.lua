import "CoreLibs/graphics"
import "CoreLibs/timer"
import "sound"
import "dial"
import "modifiers"

local gfx <const> = playdate.graphics
local pd <const> = playdate

pd.display.setRefreshRate(50)

local CX <const> = 200
local CY <const> = 128
local R <const> = 68

-- Play screen: the dial sits left of centre, in the door's recess, leaving the
-- right column for the three modifier plates. Title/lose screens keep CX/CY.
local PLAY_CX <const> = 122
local PLAY_CY <const> = 120
local PLAY_R <const> = 52
local WELL_R <const> = 64
-- Three plates fill the door's right column: 20..214, three 58s and two 10 gaps.
local CARD_X <const> = 226
local CARD_Y <const> = 20
local CARD_W <const> = 148
local CARD_H <const> = 58
local CARD_GAP <const> = 68
local DEG_PER_UNIT <const> = 3.6
local TOL <const> = 2.2
-- Speed gates are in dial units per SECOND, not per frame. Per-frame thresholds
-- silently get stricter whenever the frame rate dips: at 22 fps the same hand
-- speed produces 2.3x the per-frame delta, so a normal crank reads as TOO FAST.
-- 25/s and 80/s are the old 0.5 and 1.6 per frame at the 50 fps target.
-- The latch ceiling is per-run now (HAIR TRIGGER lowers it), so it lives in
-- Mods.buildCfg as cfg.maxEngage and is read from there. 25/sec is its default.
local RESET_SPEED <const> = 80
local DEAD_SPEED <const> = 1.5
local TINY_TICK_SPEED <const> = 80
local TICK_STEP <const> = 4
local GAME_MS <const> = 60 * 1000
local EXIT_MS <const> = 420
local DIRS <const> = { 1, -1, 1 }

local STATE_TITLE <const> = 1
local STATE_PLAY <const> = 2
local STATE_WIN <const> = 3
local STATE_LOSE <const> = 4
local STATE_TOTITLE <const> = 5
local STATE_MENU <const> = 6

local sfxImages = {
    kchik = Art.makeSfx("K-CHIK!", 1.3),
    kchunk = Art.makeSfx("K-CHUNK!", 1.4),
    open = Art.makeSfx("SAFE OPEN!", 2.1, false),
    timeup = Art.makeSfx("TIME'S UP", 2.1, false),
    title = Art.makeSfx("SAFU", 2.0, false),
    menuLogo = Art.makeSfx("SAFU", 0.9, false),
    toofast = Art.makeSfx("TOO FAST", 1.1),
    reset = Art.makeSfx("RESET!", 1.2),
    locked = Art.makeSfx("LOCKED!", 1.2),
    caught = Art.makeSfx("CAUGHT!", 2.1, false),
    boom = Art.makeSfx("BOOM!", 2.1, false),
    -- GUARD's `// \\`: built by hand rather than set in the SFX font, which has
    -- no slash glyphs, but the same frames/fades shape as the rest.
    marks = Art.makeMarks(1.2),
}
local tinyTick = Art.makeTiny("tik")
local showFps = false

local state = STATE_TITLE
local rawPos, posOffset, dialPos = 0, 0, 0
local lastDetent = 0
local targets = {}
local tumbler = 1
local armed = true
local remaining = GAME_MS
local shakeStart = -9999
local effects = {}
local lastTinyTick = 0
local winPhase, winClock = 0, 0
local losePhase, loseClock = 0, 0
local losePanel = nil
-- pause menu
local menuImage = nil
local menuIndex = 1
local menuPage = "main"
local menuClock = 0
local modsPage = 1
local MENU_ITEMS <const> = { "Resume", "Modifiers", "Quit" }
local doorImage = nil
-- The door, the dial well, the timer plate chrome and the three modifier cards
-- never change during a run, so they are drawn once into this image and blitted
-- each frame. Rebuilding them per frame cost 33 ms on device (see game.md §14).
local bgImage = nil
local timerTX, timerTY = 0, 0
local winPanel = nil
local exitImage = nil
local exitClock = 0
local lastTime = pd.getCurrentTimeMilliseconds()

-- The modifiers rolled for this run. The HUD only draws them; the effects work
-- reads Run.mods / Run.has(id) and is free to change behaviour from there.
Run = { mods = {}, mode = "normal", cfg = nil, dirs = DIRS }

-- Modifier working state, all reset by startGame.
local vel = 0              -- GREASED: coasting velocity
local stickHeld = 0        -- STICKY: input banked below the stiction threshold
local decoyTarget = nil    -- DECOY: the spot that lies
local decoyArmed = true
local driftSign = 1        -- WANDERING: which way the spots creep
local guardAt = 0          -- GUARD: when the next footstep fires
local guardDeadline = nil  -- GUARD: when being caught is decided
local nitroNeutral = 0     -- NITRO: calibrated resting tilt
local nitroCal = 0
local wrongTold = true     -- SCRAMBLED: one wrong-direction tell per zone entry
local loseReason = "timeup"
-- Tilt away from the calibrated neutral, in g on the x axis only, that spills it.
local NITRO_LIMIT <const> = 0.35
-- BLACKOUT's flashlight sits below the bottom edge, under the card column.
local FLASH_X <const> = 300
local FLASH_Y <const> = 272
local blackoutBg = nil
local notes = {}           -- TOO LOUD: music notes crossing the screen
local noteAt = 0
local noteBurst = nil
local nitroAngle, nitroVel = 0, 0   -- NITRO: sloshing surface
local NITRO_CAL_FRAMES <const> = 30
local GUARD_GRACE_MS <const> = 3000

function Run.has(id)
    for _, m in ipairs(Run.mods) do
        if m.id == id then return true end
    end
    return false
end

local function now()
    return pd.getCurrentTimeMilliseconds()
end

local function wrapDist(a, b)
    return math.abs(((a - b + 50) % 100) - 50)
end

-- Targets are built from GAPS rather than by guessing positions and rejecting
-- the bad ones.
--
-- Rejection sampling looks fine at three tumblers and is a trap at four: the
-- start plus four targets all needing 18 units of clearance wants 90 of the
-- dial's 100, so valid arrangements are so rare the loop effectively never
-- terminates. That hung the game on every FOUR TUMBLERS run.
--
-- Instead: hand out count+1 gaps that each clear `sep` and sum to exactly 100,
-- then walk them round the dial. Always succeeds, in one pass, whatever the
-- count. The shuffle at the end matters - without it the tumblers would always
-- appear in rotational order from the start position, which is a pattern a
-- player could learn to sweep.
local function genTargets(startPos, count)
    local sep = math.min(18, math.floor(100 / (count + 1)) - 4)
    local gaps = {}
    for i = 1, count + 1 do gaps[i] = sep end
    for _ = 1, 100 - (count + 1) * sep do
        local i = math.random(count + 1)
        gaps[i] = gaps[i] + 1
    end

    local t = {}
    local pos = startPos
    for i = 1, count do
        pos = (pos + gaps[i]) % 100
        t[i] = pos
    end
    for i = count, 2, -1 do
        local j = math.random(i)
        t[i], t[j] = t[j], t[i]
    end
    return t
end

local function addEffect(set, x, y, life)
    -- BLACKOUT: nothing is drawn but the timer and the cards, so an effect added
    -- during play could never be seen. Dropped here rather than at drawEffects so
    -- no object is allocated for it. End screens still get theirs - by then the
    -- state has already moved off STATE_PLAY.
    if state == STATE_PLAY and Run.cfg and not Run.cfg.showEffects then return end
    effects[#effects + 1] = { set = set, x = x, y = y, born = now(), life = life }
end

local function dialGeom()
    if state == STATE_PLAY or state == STATE_WIN then
        return PLAY_CX, PLAY_CY, PLAY_R
    end
    return CX, 126, 62
end

local function placeAround(set, spread)
    local cx, cy, r = dialGeom()
    local a = math.random() * math.pi * 2
    local x = cx + math.cos(a) * (r + spread)
    local y = cy + math.sin(a) * (r + spread * 0.6)
    x = math.max(set.hw + 10, math.min(390 - set.hw, x))
    y = math.max(set.hh + 10, math.min(230 - set.hh, y))
    return x, y
end

local function startGame()
    math.randomseed(now())
    rawPos = math.random(0, 99)
    posOffset = 0
    dialPos = rawPos % 100
    -- roll returns nil only if 500 attempts all hit a banned pair, which 182
    -- playable triples out of 220 makes vanishingly unlikely - but Run.has()
    -- iterates this, so it may never be nil.
    local picked, mode = Mods.roll(3)
    Run.mods, Run.mode = picked or {}, mode or "normal"
    Run.cfg = Mods.buildCfg(Run.mods)
    Run.dirs = Mods.rollDirs(Run.cfg.tumblers, Run.cfg.randomDirs)
    targets = genTargets(dialPos, Run.cfg.tumblers)

    -- DECOY gets its own spot, held clear of the real ones and of the start so it
    -- can never be mistaken for one by position alone - only by sound.
    decoyTarget = nil
    if Run.cfg.decoy then
        for _ = 1, 200 do
            local n = math.random(0, 99)
            local ok = wrapDist(n, dialPos) >= 18
            for _, v in ipairs(targets) do
                if wrapDist(n, v) < 18 then ok = false end
            end
            if ok then
                decoyTarget = n
                break
            end
        end
    end
    decoyArmed = true
    vel, stickHeld = 0, 0
    driftSign = (math.random(2) == 1) and 1 or -1
    guardDeadline = nil
    guardAt = now() + math.random(5000, 9000)
    nitroNeutral, nitroCal = 0, 0
    Run.tilt = 0
    nitroAngle, nitroVel = 0, 0
    notes = {}
    noteAt = now() + 600
    blackoutBg = nil
    wrongTold = true
    loseReason = "timeup"
    if Run.cfg.nitro then pd.startAccelerometer() else pd.stopAccelerometer() end
    bgImage = nil
    tumbler = 1
    armed = true
    lastDetent = math.floor(dialPos / TICK_STEP)
    remaining = GAME_MS
    shakeStart = -9999
    effects = {}
    winPhase = 0
    winClock = 0
    losePhase = 0
    loseClock = 0
    losePanel = nil
    doorImage = nil
    winPanel = nil
    exitImage = nil
    state = STATE_PLAY
    Sfx.setMechVolume(Run.cfg.mechVol)
    Sfx.start()
    Sfx.bgmStart(Run.cfg.bgmTrack, Run.cfg.bgmVol)
end

-- milliseconds in the current frame, for turning per-frame deltas into per-second
local frameMs = 20

local function unitsPerSec(delta)
    return math.abs(delta) * 1000 / math.max(frameMs, 1)
end

local function readCrank()
    local change = pd.getCrankChange()
    local delta = change / DEG_PER_UNIT
    -- Play only. Run.cfg outlives the run, so without the state check the title
    -- screen's dial would still be sticky or coasting after a modified game.
    local cfg = (state == STATE_PLAY) and Run.cfg or nil

    if cfg then
        -- STICKY: below the threshold the dial does not budge, but the input is
        -- banked and released in one shove once you push hard enough. The shove
        -- can carry you straight through a sweet spot; that is the modifier.
        if cfg.stiction > 0 then
            if unitsPerSec(delta) < cfg.stiction then
                stickHeld = stickHeld + delta
                if math.abs(stickHeld) > 40 then stickHeld = 40 * (stickHeld > 0 and 1 or -1) end
                delta = 0
            else
                delta = delta + stickHeld
                stickHeld = 0
            end
        end
        -- GREASED: follow the crank exactly while it turns, then coast. Coasting
        -- still ticks and can still graze - it is real movement.
        if cfg.friction then
            if math.abs(delta) > 0.001 then vel = delta else vel = vel * cfg.friction end
            delta = vel
        end
    end

    rawPos = rawPos + delta
    dialPos = (rawPos + posOffset) % 100
    return delta
end

local function doTicks(delta)
    local detent = math.floor(dialPos / TICK_STEP)
    if detent ~= lastDetent then
        lastDetent = detent
        local speed = unitsPerSec(delta)
        Sfx.tick(speed)
        if speed < TINY_TICK_SPEED and now() - lastTinyTick > 900 and math.random() < 0.14 then
            lastTinyTick = now()
            local x, y = placeAround(tinyTick, 34)
            addEffect(tinyTick, x, y, 420)
        end
    end
end

local function resetProgress(set)
    if tumbler > 1 then
        tumbler = 1
        Sfx.reset()
        local x, y = placeAround(set, 30)
        addEffect(set, x, y, 640)
    end
    armed = wrapDist(dialPos, targets[1]) > TOL
end

-- Every way a run ends other than the clock: ONE SHOT's wrong pull, GUARD's
-- footsteps, NITRO's spill. Same slide-down ending as a time-out, different word.
local function loseRun(reason)
    if state ~= STATE_PLAY then return end
    loseReason = reason
    state = STATE_LOSE
    losePhase = 1
    loseClock = 0
    Sfx.fail()
    Sfx.bgmStop()
    pd.stopAccelerometer()
    effects = {}
    addEffect(sfxImages[reason == "boom" and "boom" or "caught"], 200, 78, 100000)
end

local function openSafe()
    pd.stopAccelerometer()
    Sfx.bgmStop()
    Sfx.handle()
    shakeStart = now()
    local x, y = placeAround(sfxImages.kchunk, 32)
    addEffect(sfxImages.kchunk, x, y, 900)
    state = STATE_WIN
    winPhase = 1
    winClock = 0
end

local function tryHandle()
    if tumbler > Run.cfg.tumblers then
        openSafe()
        return
    end
    Sfx.locked()
    -- ONE SHOT: a wrong pull is the end of the run, not a reset.
    if Run.cfg.oneShot then
        local x, y = placeAround(sfxImages.locked, 30)
        addEffect(sfxImages.locked, x, y, 640)
        loseRun("caught")
        return
    end
    if tumbler > 1 then Sfx.reset() end
    tumbler = 1
    armed = wrapDist(dialPos, targets[1]) > TOL
    local x, y = placeAround(sfxImages.locked, 30)
    addEffect(sfxImages.locked, x, y, 640)
end

-- DECOY. Latches like a real spot and sounds almost like one, but never
-- advances and never shakes the screen. Those two absences - the dud in the
-- tail, the missing shake - are the only tells, one per channel.
local function checkDecoy(delta, speed)
    local cfg = Run.cfg
    if not cfg.decoy or not decoyTarget then return end
    if wrapDist(dialPos, decoyTarget) > TOL then
        decoyArmed = true
        return
    end
    if not decoyArmed then return end
    if speed < DEAD_SPEED or speed > cfg.maxEngage then return end
    local need = Run.dirs[math.min(tumbler, cfg.tumblers)] or 1
    if (delta > 0 and 1 or -1) ~= need then return end
    decoyArmed = false
    Sfx.decoy()
    local x, y = placeAround(sfxImages.kchik, 32)
    addEffect(sfxImages.kchik, x, y, 680)
end

local function checkTumbler(delta)
    local cfg = Run.cfg
    local speed = unitsPerSec(delta)
    if speed > RESET_SPEED then
        resetProgress(sfxImages.reset)
        return
    end
    checkDecoy(delta, speed)
    if tumbler > cfg.tumblers then return end

    local target = targets[tumbler]
    local need = Run.dirs[tumbler]
    local inZone = wrapDist(dialPos, target) <= TOL

    if not inZone then
        armed = true
        wrongTold = false
        return
    end
    if not armed then return end
    if speed < DEAD_SPEED then return end
    local dir = delta > 0 and 1 or -1
    if dir ~= need then
        -- SCRAMBLED hides which way each tumbler wants, so passing over one the
        -- wrong way has to say something. Once per entry, or it machine-guns.
        if cfg.randomDirs and not wrongTold then
            wrongTold = true
            Sfx.wrongDir()
        end
        return
    end

    if speed > cfg.maxEngage then
        armed = false
        Sfx.graze()
        local x, y = placeAround(sfxImages.toofast, 30)
        addEffect(sfxImages.toofast, x, y, 620)
        if tumbler > 1 then
            tumbler = 1
            Sfx.reset()
        end
        return
    end

    armed = false
    local diff = ((target - dialPos + 50) % 100) - 50
    posOffset = posOffset + diff
    dialPos = (rawPos + posOffset) % 100
    lastDetent = math.floor(dialPos / TICK_STEP)
    if cfg.shake then shakeStart = now() end

    tumbler = tumbler + 1
    Sfx.sweetSpot()
    local x, y = placeAround(sfxImages.kchik, 32)
    addEffect(sfxImages.kchik, x, y, 680)
    if tumbler <= cfg.tumblers then
        armed = wrapDist(dialPos, targets[tumbler]) > TOL
    end
end

local function formatTime(ms)
    if ms < 0 then ms = 0 end
    local total = math.floor(ms)
    local m = math.floor(total / 60000)
    local s = math.floor(total / 1000) % 60
    local c = math.floor(total / 10) % 100
    return string.format("%02d:%02d.%02d", m, s, c)
end

-- Every Ⓐ/Ⓑ prompt in the game: a 14x14 button glyph and a 13px label, the pair
-- centred on cx and on each other. `y` is the top of the glyph.
local ICON <const> = 14
local ICON_GAP <const> = 5

local function drawIconLabel(icon, text, cx, y, white)
    gfx.setFont(Art.numFont)
    local tw = gfx.getTextSize(text)
    -- measure before switching draw mode; inkBand needs to draw black on white
    local inkTop, inkH = Art.inkBand(Art.numFont, Art.CAPS)
    local x = math.floor(cx - (ICON + ICON_GAP + tw) / 2)
    if white then gfx.setImageDrawMode(gfx.kDrawModeFillWhite) end
    icon:draw(x, y)
    gfx.drawText(text, x + ICON + ICON_GAP, y + math.floor((ICON - inkH) / 2) - inkTop)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
end

local function buildBackground()
    local img = gfx.image.new(400, 240)
    gfx.pushContext(img)
        Art.drawDoor()
        Art.drawDialWell(PLAY_CX, PLAY_CY, WELL_R)
        timerTX, timerTY = Art.drawTimerPlate(24, 20)
        for i, m in ipairs(Run.mods or {}) do
            Art.drawModCard(CARD_X, CARD_Y + (i - 1) * CARD_GAP, CARD_W, CARD_H,
                Mods.iconImage(m.icon), m.name, m.sub)
        end
    gfx.popContext()
    return img
end

local function drawHud()
    Art.drawTimerText(timerTX, timerTY, formatTime(remaining))
    -- ONE SHOT: the prompt shakes, because pressing it wrongly ends the run.
    -- Flavour, not information - the card already states the rule, which is why
    -- losing this under BLACKOUT costs the player nothing.
    local tx = 0
    if Run.cfg and Run.cfg.oneShot then tx = math.sin(now() / 26) * 1.6 end
    drawIconLabel(Art.iconA, "OPEN?", PLAY_CX + tx, 186, false)
    drawIconLabel(Art.iconB, "MENU", PLAY_CX, 204, false)
    if showFps then pd.drawFPS(370, 224) end
end

local WIGGLE_MS <const> = 34
local FADE_MS <const> = 200

local function drawEffects()
    local t = now()
    local i = 1
    while i <= #effects do
        local e = effects[i]
        local age = t - e.born
        if age > e.life then
            table.remove(effects, i)
        else
            local set = e.set
            local frame
            local dy = 0
            local outStart = e.life - FADE_MS
            if age >= outStart then
                local q = (age - outStart) / FADE_MS
                local idx = math.max(1, math.min(#set.fades, math.ceil(q * #set.fades)))
                frame = set.fades[idx]
                dy = -10 * q
            else
                local idx = math.floor(age / WIGGLE_MS) + 1
                if idx > #set.frames then idx = #set.frames end
                frame = set.frames[idx]
            end
            frame.img:draw(e.x - frame.hw, e.y - frame.hh + dy)
            i = i + 1
        end
    end
end

-- BLACKOUT. The room is dark: the whole screen is black and only the timer and
-- the three cards exist, the cards lit by a flashlight from below the bottom
-- edge. Everything is static except the timer digits, so it is baked once.
local function buildBlackout()
    local mask = gfx.image.new(400, 240, gfx.kColorBlack)
    gfx.pushContext(mask)
        Art.drawLightMask(FLASH_X, FLASH_Y)
    gfx.popContext()

    local img = gfx.image.new(400, 240, gfx.kColorBlack)
    gfx.pushContext(img)
        -- the beam first, so the cone is visible in the empty dark and not only
        -- wherever it happens to land on a card
        Art.drawLightBeam(FLASH_X, FLASH_Y)
        -- then the cards through it, dimming toward the top of the throw
        gfx.setStencilImage(mask)
        for i, m in ipairs(Run.mods or {}) do
            Art.drawModCard(CARD_X, CARD_Y + (i - 1) * CARD_GAP, CARD_W, CARD_H,
                Mods.iconImage(m.icon), m.name, m.sub)
        end
        gfx.clearStencil()
        -- the timer is unaffected by the blackout, so it is drawn outside the cone
        timerTX, timerTY = Art.drawTimerPlate(24, 20)
    gfx.popContext()
    return img
end

local function drawNotes()
    if #notes == 0 or not noteBurst then return end
    for _, nt in ipairs(notes) do
        noteBurst.img:draw(nt.x - noteBurst.hw, nt.y - noteBurst.hh)
    end
end

local function drawNitro()
    if not (Run.cfg and Run.cfg.nitro) then return end
    Art.drawWaterLayer(nitroAngle, math.min(math.abs(Run.tilt or 0) / NITRO_LIMIT, 1))
end

local function drawScene()
    local cfg = Run.cfg
    if cfg and not cfg.drawDial then
        if not blackoutBg then blackoutBg = buildBlackout() end
        blackoutBg:draw(0, 0)
        Art.drawTimerText(timerTX, timerTY, formatTime(remaining))
        if showFps then pd.drawFPS(370, 224) end
        -- no dial, no shake, no SFX text, and no Ⓐ prompt: the run is played by ear
        return
    end

    if not bgImage then bgImage = buildBackground() end
    bgImage:draw(0, 0)
    local ox, oy = 0, 0
    local sage = now() - shakeStart
    if sage < 220 then
        local amp = 4.5 * (1 - sage / 220)
        ox = math.sin(sage / 15) * amp
        oy = math.cos(sage / 11) * amp * 0.7
    end
    Art.drawDial(PLAY_CX + ox, PLAY_CY + oy, PLAY_R, dialPos)
    drawHud()
    drawEffects()
    drawNotes()
    drawNitro()   -- last: the spirit level sits over everything
end

-- WANDERING: the spots creep only while the dial is still, so holding steady to
-- think is what costs you and cranking is the counter. Already-latched spots are
-- left alone. Capped at Mods.MAX_DRIFT, well under the latch ceiling.
local function driftTargets(dt, speed)
    local cfg = Run.cfg
    if cfg.drift <= 0 or speed >= DEAD_SPEED then return end
    local d = cfg.drift * dt / 1000 * driftSign
    for i = tumbler, cfg.tumblers do
        if targets[i] then targets[i] = (targets[i] + d) % 100 end
    end
end

-- GUARD: footsteps, then three seconds to bring the dial to a stop. Still moving
-- when the grace runs out and the guard has you. The grace exists so the cue is
-- always reactable - punishing on the sound itself would be unfair.
local function updateGuard(speed)
    if not Run.cfg.guard then return end
    local t = now()
    if guardDeadline then
        if t >= guardDeadline then
            if speed > DEAD_SPEED then
                loseRun("caught")
                return
            end
            guardDeadline = nil
            guardAt = t + math.random(5000, 9000)
        end
    elseif t >= guardAt then
        Sfx.footstep()
        local x, y = placeAround(sfxImages.marks, 30)
        addEffect(sfxImages.marks, x, y, 900)
        guardDeadline = t + GUARD_GRACE_MS
    end
end

-- NITRO: x axis only, so it is a left/right balance rather than a full 3D pose.
-- The first frames of a run calibrate whatever angle the player actually holds
-- the device at, so nobody is punished for their grip.
local function updateNitro()
    if not Run.cfg.nitro then return end
    local x = pd.readAccelerometer()
    if not x then return end
    if nitroCal < NITRO_CAL_FRAMES then
        nitroCal = nitroCal + 1
        nitroNeutral = nitroNeutral + (x - nitroNeutral) * 0.25
        return
    end
    Run.tilt = x - nitroNeutral
    if math.abs(Run.tilt) > NITRO_LIMIT then loseRun("boom") end
end

-- TOO LOUD: the club is loud enough to see. Notes launch off the top edge on a
-- random diagonal, left or right, and simply leave the screen - no fade, so
-- nothing pops out of existence mid-flight.
local function updateNotes(dt)
    if Run.has("too-loud") and now() >= noteAt then
        if not noteBurst then noteBurst = Art.makeNoteBurst(Mods.iconImage("music-note")) end
        local dir = (math.random(2) == 1) and 1 or -1
        local ang = math.rad(math.random(20, 58)) * dir
        -- Left of the card column only. A note crossing a card wrecks the one
        -- thing the player must always be able to read.
        notes[#notes + 1] = {
            x = math.random(45, 175), y = -14,
            vx = math.sin(ang) * 0.13, vy = math.cos(ang) * 0.13,
        }
        noteAt = now() + math.random(700, 1500)
    end
    local i = 1
    while i <= #notes do
        local nt = notes[i]
        nt.x = nt.x + nt.vx * dt
        nt.y = nt.y + nt.vy * dt
        if nt.y > 252 or nt.x < -40 or nt.x > 205 then table.remove(notes, i) else i = i + 1 end
    end
end

-- A damped spring, so the surface overshoots and settles instead of snapping to
-- the device angle. That lag is what makes it read as liquid.
local function updateSlosh()
    if not Run.cfg.nitro then return end
    local target = -(Run.tilt or 0) * 0.8
    nitroVel = (nitroVel + (target - nitroAngle) * 0.06) * 0.88
    nitroAngle = nitroAngle + nitroVel
end

local function updatePlay(dt)
    frameMs = dt
    if pd.isCrankDocked() then
        gfx.setColor(gfx.kColorBlack)
        return
    end
    remaining = remaining - dt
    local delta = readCrank()
    doTicks(delta)
    if state == STATE_PLAY then
        local speed = unitsPerSec(delta)
        checkTumbler(delta)
        driftTargets(dt, speed)
        updateGuard(speed)
        updateNitro()
        updateSlosh()
    end
    updateNotes(dt)
    if remaining <= 0 and state == STATE_PLAY then
        remaining = 0
        loseReason = "timeup"
        state = STATE_LOSE
        losePhase = 1
        loseClock = 0
        Sfx.fail()
        Sfx.bgmStop()
        pd.stopAccelerometer()
        effects = {}
        addEffect(sfxImages.timeup, 200, 78, 100000)
    end
end

local DOCKED_TEXT <const> = "UNDOCK THE CRANK"

local function drawDockedNotice()
    local bx, by, bw, bh <const> = 74, 96, 252, 48
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(bx, by, bw, bh, 8)
    gfx.setFont(Art.uiFont)
    -- centre on the text's ink, not its line box, or it sits high in the panel
    local inkTop, inkH = Art.inkBand(Art.uiFont, Art.CAPS)
    gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    gfx.drawTextAligned(DOCKED_TEXT, bx + math.floor(bw / 2),
        by + math.floor((bh - inkH) / 2) - inkTop, kTextAlignment.center)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
end

local function buildWinPanel()
    local img = gfx.image.new(400, 240, gfx.kColorBlack)
    gfx.pushContext(img)
        local f = sfxImages.open.frames[1]
        f.img:draw(200 - f.hw, 76 - f.hh)
        gfx.setFont(Art.uiFont)
        gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
        gfx.drawTextAligned("TIME LEFT", 200, 118, kTextAlignment.center)
        gfx.setFont(Art.timerFont)
        gfx.drawTextAligned(formatTime(remaining), 200, 138, kTextAlignment.center)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        drawIconLabel(Art.iconA, "AGAIN", 200, 184, true)
        drawIconLabel(Art.iconB, "TITLE", 200, 210, true)
    gfx.popContext()
    return img
end

local function buildLosePanel()
    local img = gfx.image.new(400, 240, gfx.kColorBlack)
    gfx.pushContext(img)
        local key = loseReason == "boom" and "boom"
            or (loseReason == "caught" and "caught" or "timeup")
        local f = sfxImages[key].frames[1]
        f.img:draw(200 - f.hw, 76 - f.hh)
        gfx.setFont(Art.uiFont)
        gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
        gfx.drawTextAligned("TUMBLERS FOUND", 200, 118, kTextAlignment.center)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
        Art.drawDots(200, 146, tumbler - 1, true, Run.cfg and Run.cfg.tumblers or 3)
        drawIconLabel(Art.iconA, "TRY AGAIN", 200, 180, true)
        drawIconLabel(Art.iconB, "TITLE", 200, 206, true)
    gfx.popContext()
    return img
end

-- The lose panel slides down over the frozen scene, the mirror of the win panel
-- and of the Ⓑ slide-up back to the title.
local function updateLose(dt)
    loseClock = loseClock + dt
    readCrank()
    if losePhase == 1 and loseClock > 700 then
        doorImage = gfx.getDisplayImage()
        losePanel = buildLosePanel()
        losePhase = 2
        loseClock = 0
    elseif losePhase == 2 and loseClock > 460 then
        losePhase = 3
        loseClock = 0
    end
end

local function updateWin(dt)
    winClock = winClock + dt
    readCrank()
    if winPhase == 1 and winClock > 800 then
        doorImage = gfx.getDisplayImage()
        winPanel = buildWinPanel()
        winPhase = 2
        winClock = 0
    elseif winPhase == 2 and winClock > 460 then
        winPhase = 3
        winClock = 0
    end
end

local function drawWin()
    if winPhase == 1 then
        drawScene()
        return
    end
    if winPhase == 2 then
        doorImage:draw(0, 0)
        local t = math.min(winClock / 460, 1)
        local e = 1 - (1 - t) * (1 - t) * (1 - t)
        winPanel:draw(0, math.floor(-240 + 240 * e))
    else
        winPanel:draw(0, 0)
    end
end

local function drawLose()
    if losePhase == 1 then
        drawScene()
        return
    end
    if losePhase == 2 then
        doorImage:draw(0, 0)
        local t = math.min(loseClock / 460, 1)
        local e = 1 - (1 - t) * (1 - t) * (1 - t)
        losePanel:draw(0, math.floor(-240 + 240 * e))
    else
        losePanel:draw(0, 0)
    end
end

local function drawTitle()
    gfx.clear(gfx.kColorWhite)
    Art.drawDial(CX, 126, 62, dialPos)
    local tf = sfxImages.title.frames[1]
    tf.img:draw(200 - tf.hw, 40 - tf.hh)
    gfx.setFont(Art.uiFont)
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(120, 204, 160, 30, 6)
    drawIconLabel(Art.iconA, "CRACK IT", 200, 212, true)
end

local function startToTitle()
    -- Quitting mid-run leaves the play BGM running otherwise
    Sfx.titleAudio()
    exitImage = gfx.getDisplayImage()
    exitClock = 0
    effects = {}
    state = STATE_TOTITLE
end

local function drawToTitle()
    drawTitle()
    local t = math.min(exitClock / EXIT_MS, 1)
    local e = 1 - (1 - t) * (1 - t) * (1 - t)
    exitImage:draw(0, math.floor(-240 * e))
end

-- ---------------------------------------------------------------------------
-- Pause menu. Everything behind it is frozen: the screen is captured on open and
-- blitted underneath, and update() runs none of the play logic while it is up.

local function openMenu()
    menuImage = gfx.getDisplayImage()
    menuIndex = 1
    menuPage = "main"
    menuClock = 0
    state = STATE_MENU
end

local function closeMenu()
    menuImage = nil
    state = STATE_PLAY
end

-- The panel is sized to its content and no larger, and symmetrically: the cursor
-- gutter is mirrored on the right so the centred labels sit in the middle, and
-- the height counts the last row's ink rather than a full line of leading.
local CURSOR_W <const> = 16
local CURSOR_GAP <const> = 6

local function menuBox(measures, rowCount, rowH, lastRowInk, topExtra, minW)
    local w = 0
    for _, m in ipairs(measures) do
        gfx.setFont(m[2])
        local lw = gfx.getTextSize(m[1])
        if lw > w then w = lw end
    end
    local PADX <const>, PADY <const> = 14, 12
    local gutter = CURSOR_W + CURSOR_GAP
    local boxW = math.max(PADX * 2 + gutter * 2 + w, minW or 0)
    local boxH = PADY * 2 + (topExtra or 0) + (rowCount - 1) * rowH + (lastRowInk or rowH)
    return math.floor(200 - boxW / 2), math.floor(120 - boxH / 2), boxW, boxH, PADX, PADY
end

-- Pokes at the row along X rather than rotating, so it reads as pointing.
local function drawCursor(x, y)
    local poke = math.floor((math.sin(menuClock / 170) + 1) * 2.5)
    Art.iconHand:draw(x + poke, y)
end

local function drawMenu()
    if menuImage then menuImage:draw(0, 0) end
    gfx.setColor(gfx.kColorBlack)
    gfx.setDitherPattern(0.5, gfx.image.kDitherTypeBayer4x4)
    gfx.fillRect(0, 0, 400, 240)
    gfx.setColor(gfx.kColorBlack)

    if menuPage == "mods" then
        -- Catalogue of every modifier, not just this run's: 12 across two pages,
        -- a 2x3 grid of cells laid out like the door's modifier cards.
        local COLS <const>, ROWS <const> = 2, 3
        local PER <const> = COLS * ROWS
        -- Sized to the content, not the screen: a cell only has to hold the
        -- longest title (FOUR TUMBLERS, 107px + the 20px icon column) and wrap
        -- the longest subtitle (188px) onto two lines.
        local CELL_W <const>, CELL_H <const> = 134, 44
        local COL_GAP <const>, ROW_GAP <const> = 10, 6
        local PADX <const>, PADY <const> = 14, 10
        local boxW = PADX * 2 + COLS * CELL_W + COL_GAP
        local boxH = PADY * 2 + ROWS * CELL_H + (ROWS - 1) * ROW_GAP + 14
        local bx, by = math.floor(200 - boxW / 2), math.floor(120 - boxH / 2)
        Art.drawPlate(bx, by, boxW, boxH)

        local pages = math.ceil(#Mods.list / PER)
        local first = (modsPage - 1) * PER + 1
        for i = 0, PER - 1 do
            local m = Mods.list[first + i]
            if m then
                local cx = bx + PADX + (i % COLS) * (CELL_W + COL_GAP)
                local cy = by + PADY + math.floor(i / COLS) * (CELL_H + ROW_GAP)
                local icon = Mods.iconImage(m.icon)
                if icon then icon:draw(cx, cy + 1) end
                local tx = cx + 20
                gfx.setFont(Art.titleFont)
                gfx.drawText(m.name, tx, cy)
                gfx.setFont(Art.subFont)
                gfx.drawTextInRect(m.sub, tx, cy + 15, CELL_W - 20, 26)
            end
        end

        gfx.setFont(Art.numFont)
        gfx.drawTextAligned(string.format("< %d/%d >", modsPage, pages),
            200, by + boxH - 16, kTextAlignment.center)
        return
    end

    local rowH <const> = 20
    local measures = {}
    for i, l in ipairs(MENU_ITEMS) do measures[i] = { l, Art.numFont } end
    gfx.setFont(Art.numFont)
    local inkTop, inkH = Art.inkBand(Art.numFont, Art.CAPS)
    -- the last row sets the bottom gap, so measure ITS ink: "Quit" descends
    local lastTop, lastH = Art.inkBand(Art.numFont, MENU_ITEMS[#MENU_ITEMS])

    -- The logo is centred on the top border, so its lower half hangs into the
    -- panel. The first row clears that, not that PLUS the normal padding.
    local lg = sfxImages.menuLogo.frames[1]
    local PADY <const> = 12
    local contentTop = math.max(PADY, lg.hh - 6)
    local x, y, w, h, padX, padY =
        menuBox(measures, #MENU_ITEMS, rowH, lastTop + lastH, contentTop - PADY, lg.hw * 2 + 28)
    Art.drawPanel(x, y, w, h)

    for i, label in ipairs(MENU_ITEMS) do
        local ry = y + contentTop + (i - 1) * rowH
        local lw = gfx.getTextSize(label)
        local lx = math.floor(200 - lw / 2)
        if i == menuIndex then
            drawCursor(lx - CURSOR_GAP - CURSOR_W, ry + inkTop + math.floor((inkH - 16) / 2))
        end
        gfx.drawText(label, lx, ry)
    end

    lg.img:draw(200 - lg.hw, y - lg.hh)
end

local function updateMenu(dt)
    menuClock = menuClock + dt
    pd.getCrankChange()   -- drain, or the crank jumps when play resumes
    if menuPage == "mods" then
        local pages = math.ceil(#Mods.list / 6)
        if pd.buttonJustPressed(pd.kButtonRight) or pd.buttonJustPressed(pd.kButtonDown) then
            modsPage = modsPage % pages + 1
            Sfx.uiHover()
        elseif pd.buttonJustPressed(pd.kButtonLeft) or pd.buttonJustPressed(pd.kButtonUp) then
            modsPage = (modsPage - 2) % pages + 1
            Sfx.uiHover()
        elseif pd.buttonJustPressed(pd.kButtonB) then
            Sfx.uiBack()
            menuPage = "main"
        end
        return
    end
    if pd.buttonJustPressed(pd.kButtonUp) then
        menuIndex = (menuIndex - 2) % #MENU_ITEMS + 1
        Sfx.uiHover()
    elseif pd.buttonJustPressed(pd.kButtonDown) then
        menuIndex = menuIndex % #MENU_ITEMS + 1
        Sfx.uiHover()
    elseif pd.buttonJustPressed(pd.kButtonB) then
        Sfx.uiBack()
        closeMenu()
    elseif pd.buttonJustPressed(pd.kButtonA) then
        local pick = MENU_ITEMS[menuIndex]
        if pick == "Resume" then
            Sfx.uiBack()
            closeMenu()
        elseif pick == "Modifiers" then
            Sfx.uiConfirm()
            menuPage = "mods"
            modsPage = 1
        else
            Sfx.uiConfirm()
            menuImage = nil
            startToTitle()
        end
    end
end

function pd.update()
    local t = now()
    local dt = t - lastTime
    lastTime = t
    if dt > 120 then dt = 120 end

    if state == STATE_TITLE then
        readCrank()
        doTicks(0)
        drawTitle()
        if pd.buttonJustPressed(pd.kButtonA) then startGame() end
    elseif state == STATE_PLAY then
        if pd.buttonJustPressed(pd.kButtonB) then
            -- Open and draw, but do NOT run updateMenu this frame: buttonJustPressed
            -- is still true for the rest of it, and the menu's own Ⓑ handler would
            -- read the same press and close again immediately.
            Sfx.uiConfirm()
            drawScene()          -- freeze a current frame for the menu to sit on
            openMenu()
            drawMenu()
        else
            if pd.buttonJustPressed(pd.kButtonA) and not pd.isCrankDocked() then tryHandle() end
            local docked = pd.isCrankDocked()
            updatePlay(dt)
            if state == STATE_PLAY then
                drawScene()
                if docked then drawDockedNotice() end
            elseif state == STATE_WIN then
                drawScene()
            else
                drawLose()
            end
        end
    elseif state == STATE_WIN then
        updateWin(dt)
        drawWin()
        if winPhase == 3 then
            if pd.buttonJustPressed(pd.kButtonA) then startGame() end
            if pd.buttonJustPressed(pd.kButtonB) then Sfx.uiBack(); startToTitle() end
        end
    elseif state == STATE_TOTITLE then
        exitClock = exitClock + dt
        readCrank()
        doTicks(0)
        drawToTitle()
        if exitClock >= EXIT_MS then
            exitImage = nil
            state = STATE_TITLE
        end
    elseif state == STATE_MENU then
        updateMenu(dt)
        if state == STATE_MENU then drawMenu()
        elseif state == STATE_PLAY then drawScene() end
    else
        updateLose(dt)
        drawLose()
        if losePhase == 3 then
            if pd.buttonJustPressed(pd.kButtonA) then startGame() end
            if pd.buttonJustPressed(pd.kButtonB) then Sfx.uiBack(); startToTitle() end
        end
    end

    pd.timer.updateTimers()
end
