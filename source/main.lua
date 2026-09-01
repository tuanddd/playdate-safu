import "CoreLibs/graphics"
import "CoreLibs/timer"
import "sound"
import "dial"

local gfx <const> = playdate.graphics
local pd <const> = playdate

pd.display.setRefreshRate(50)

local CX <const> = 200
local CY <const> = 128
local R <const> = 68
local DEG_PER_UNIT <const> = 3.6
local TOL <const> = 2.2
local MAX_ENGAGE_SPEED <const> = 0.5
local RESET_SPEED <const> = 1.6
local TICK_STEP <const> = 4
local GAME_MS <const> = 60 * 1000
local EXIT_MS <const> = 420
local DIRS <const> = { 1, -1, 1 }

local STATE_TITLE <const> = 1
local STATE_PLAY <const> = 2
local STATE_WIN <const> = 3
local STATE_LOSE <const> = 4
local STATE_TOTITLE <const> = 5

local sfxImages = {
    kchik = Art.makeSfx("K-CHIK!", 1.3),
    kchunk = Art.makeSfx("K-CHUNK!", 1.4),
    open = Art.makeSfx("SAFE OPEN!", 2.1, false),
    timeup = Art.makeSfx("TIME'S UP", 2.1, false),
    title = Art.makeSfx("SAFU", 2.0, false),
    toofast = Art.makeSfx("TOO FAST", 1.1),
    reset = Art.makeSfx("RESET!", 1.2),
    locked = Art.makeSfx("LOCKED!", 1.2),
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
local doorImage = nil
local winPanel = nil
local exitImage = nil
local exitClock = 0
local lastTime = pd.getCurrentTimeMilliseconds()

local function now()
    return pd.getCurrentTimeMilliseconds()
end

local function wrapDist(a, b)
    return math.abs(((a - b + 50) % 100) - 50)
end

local function genTargets()
    local t = {}
    while #t < 3 do
        local n = math.random(0, 99)
        local ok = wrapDist(n, 0) >= 18
        for _, v in ipairs(t) do
            if wrapDist(n, v) < 18 then ok = false end
        end
        if ok then t[#t + 1] = n end
    end
    return t
end

local function addEffect(set, x, y, life)
    effects[#effects + 1] = { set = set, x = x, y = y, born = now(), life = life }
end

local function placeAround(set, spread)
    local a = math.random() * math.pi * 2
    local x = CX + math.cos(a) * (R + spread)
    local y = CY + math.sin(a) * (R + spread * 0.6)
    x = math.max(set.hw + 3, math.min(397 - set.hw, x))
    y = math.max(set.hh + 3, math.min(237 - set.hh, y))
    return x, y
end

local function startGame()
    math.randomseed(now())
    targets = genTargets()
    tumbler = 1
    armed = true
    rawPos = 0
    posOffset = 0
    dialPos = 0
    lastDetent = 0
    remaining = GAME_MS
    shakeStart = -9999
    effects = {}
    winPhase = 0
    winClock = 0
    doorImage = nil
    winPanel = nil
    exitImage = nil
    state = STATE_PLAY
    Sfx.start()
    Sfx.bgmStart()
end

local function readCrank()
    local change = SimCrank or pd.getCrankChange()
    local delta = change / DEG_PER_UNIT
    rawPos = rawPos + delta
    dialPos = (rawPos + posOffset) % 100
    return delta
end

local function doTicks(delta)
    local detent = math.floor(dialPos / TICK_STEP)
    if detent ~= lastDetent then
        lastDetent = detent
        local speed = math.abs(delta)
        Sfx.tick(speed)
        if speed < 1.6 and now() - lastTinyTick > 900 and math.random() < 0.14 then
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

local function openSafe()
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
    if tumbler == 4 then
        openSafe()
        return
    end
    Sfx.locked()
    if tumbler > 1 then Sfx.reset() end
    tumbler = 1
    armed = wrapDist(dialPos, targets[1]) > TOL
    local x, y = placeAround(sfxImages.locked, 30)
    addEffect(sfxImages.locked, x, y, 640)
end

local function checkTumbler(delta)
    local speed = math.abs(delta)
    if speed > RESET_SPEED then
        resetProgress(sfxImages.reset)
        return
    end
    if tumbler > 3 then return end

    local target = targets[tumbler]
    local need = DIRS[tumbler]
    local inZone = wrapDist(dialPos, target) <= TOL

    if not inZone then
        armed = true
        return
    end
    if not armed then return end
    if speed < 0.03 then return end
    local dir = delta > 0 and 1 or -1
    if dir ~= need then return end

    if speed > MAX_ENGAGE_SPEED then
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
    shakeStart = now()

    tumbler = tumbler + 1
    Sfx.sweetSpot()
    local x, y = placeAround(sfxImages.kchik, 32)
    addEffect(sfxImages.kchik, x, y, 680)
    if tumbler <= 3 then
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

local function drawIconLabel(icon, text, cx, y, white)
    gfx.setFont(Art.uiFont)
    local tw = gfx.getTextSize(text)
    local x = cx - (28 + tw) / 2
    if white then gfx.setImageDrawMode(gfx.kDrawModeFillWhite) end
    icon:draw(x, y)
    gfx.drawText(text, x + 28, y + 1)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
end

local function drawTopBar()
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(-8, -8, 198, 40, 8)
    gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    Art.iconClock:draw(10, 5)
    gfx.setFont(Art.timerFont)
    gfx.drawText(formatTime(remaining), 40, 2)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
end

local function drawHud()
    drawTopBar()
    drawIconLabel(Art.iconA, "Open?", 200, 212, false)
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

local function drawScene()
    gfx.clear(gfx.kColorWhite)
    local ox, oy = 0, 0
    local sage = now() - shakeStart
    if sage < 220 then
        local amp = 4.5 * (1 - sage / 220)
        ox = math.sin(sage / 15) * amp
        oy = math.cos(sage / 11) * amp * 0.7
    end
    Art.drawDial(CX + ox, CY + oy, R, dialPos)
    drawHud()
    drawEffects()
end

local function updatePlay(dt)
    if pd.isCrankDocked() then
        gfx.setColor(gfx.kColorBlack)
        return
    end
    remaining = remaining - dt
    local delta = readCrank()
    doTicks(delta)
    if state == STATE_PLAY then
        checkTumbler(delta)
    end
    if remaining <= 0 and state == STATE_PLAY then
        remaining = 0
        state = STATE_LOSE
        Sfx.fail()
        effects = {}
        Sfx.bgmStop()
        addEffect(sfxImages.timeup, 200, 78, 100000)
    end
end

local function drawDockedNotice()
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(74, 96, 252, 48, 8)
    gfx.setFont(Art.uiFont)
    gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    gfx.drawTextAligned("UNDOCK THE CRANK", 200, 113, kTextAlignment.center)
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
    gfx.clear(gfx.kColorBlack)
    gfx.setFont(Art.uiFont)
    gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    gfx.drawTextAligned("TUMBLERS FOUND", 200, 128, kTextAlignment.center)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    Art.drawDots(CX, 164, tumbler - 1, true)
    drawIconLabel(Art.iconA, "TRY AGAIN", 200, 190, true)
    drawIconLabel(Art.iconB, "TITLE", 200, 214, true)
    drawEffects()
end

local function drawTitle()
    gfx.clear(gfx.kColorWhite)
    Art.drawDial(CX, 126, 62, dialPos)
    local tf = sfxImages.title.frames[1]
    tf.img:draw(200 - tf.hw, 40 - tf.hh)
    gfx.setFont(Art.uiFont)
    gfx.setColor(gfx.kColorBlack)
    gfx.fillRoundRect(120, 204, 160, 30, 6)
    drawIconLabel(Art.iconA, "CRACK IT", 200, 208, true)
end

local function startToTitle()
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
        if pd.buttonJustPressed(pd.kButtonB) then showFps = not showFps end
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
    elseif state == STATE_WIN then
        updateWin(dt)
        drawWin()
        if winPhase == 3 then
            if pd.buttonJustPressed(pd.kButtonA) then startGame() end
            if pd.buttonJustPressed(pd.kButtonB) then startToTitle() end
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
    else
        drawLose()
        if pd.buttonJustPressed(pd.kButtonA) then startGame() end
        if pd.buttonJustPressed(pd.kButtonB) then startToTitle() end
    end

    pd.timer.updateTimers()
end

Sim = {
    setCrank = function(v) SimCrank = v end,
    start = function() startGame() end,
    tumbler = function() return tumbler end,
    need = function() return DIRS[math.min(tumbler, 3)] end,
    state = function() return state end,
    setRemaining = function(v) remaining = v end,
    fps = function() showFps = true end,
    handle = function() tryHandle() end,
}

import "shots"
