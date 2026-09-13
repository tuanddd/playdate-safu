local snd <const> = playdate.sound

Sfx = {}

-- ---------------------------------------------------------------------------
-- THE MIX. Every level the game can emit lives in this one table, so the debug
-- Audio page can move any of them at runtime and hear the result immediately.
--
-- Levels are stored in dB on a 0..40 scale: **0 dB is silence** and 40 dB is the
-- loudest the device will go. That is not dBFS - the SDK exposes no gain above
-- unity, so full scale is the ceiling and the natural way to express it is as a
-- level above silence rather than an attenuation below the ceiling.
--
--     linear = 10 ^ ((dB - 40) / 20)      0 dB -> 0 (forced silent)
--
-- One display dB per real dB: 40 dB is unity, 20 dB is -20 dBFS, and 0 dB sits
-- at -40 dBFS, which is silent on the device speaker and is forced to a hard
-- zero anyway. `Sfx.gain(id)` is the only way to read a level.
--
-- These defaults are the pre-mixer levels converted across, and they are not
-- precious - the debug Audio page exists to replace them by ear.
Sfx.DB_MAX = 40

Sfx.mix = {
    tick       = 28.4,
    graze      = 34.0,
    sweet      = 40.0,
    decoy      = 40.0,
    wrong      = 24.0,
    locked     = 29.6,
    reset      = 28.4,
    fail       = 29.6,
    handle     = 40.0,
    cleared    = 33.0,
    start      = 29.6,
    footstep   = 40.0,
    flashlight = 40.0,
    uiConfirm  = 40.0,
    uiBack     = 40.0,
    uiHover    = 33.0,
    keypadError = 40.0,
    bgmTitle   = 30.8,
    bgmDefault = 21.6,
    bgmClub    = 40.0,
    bgmNight   = 28.4,
}

-- dB on the 0..40 scale -> linear amplitude for the SDK.
function Sfx.gain(id)
    local d = Sfx.mix[id] or 0
    if d <= 0 then return 0 end
    if d > Sfx.DB_MAX then d = Sfx.DB_MAX end
    return 10 ^ ((d - Sfx.DB_MAX) / 20)
end

-- Display order for the debug Audio page. `track` marks the four beds: they loop
-- while selected instead of being retriggered, so a level change is heard on the
-- music that is already running.
Sfx.mixList = {
    { id = "tick",       name = "TICK",       sub = "dial detent" },
    { id = "graze",      name = "GRAZE",      sub = "spot brushed" },
    { id = "sweet",      name = "LATCH",      sub = "real sweet spot" },
    { id = "decoy",      name = "DECOY",      sub = "fake latch" },
    { id = "wrong",      name = "WRONG WAY",  sub = "scrambled tell" },
    { id = "locked",     name = "LOCKED",     sub = "tumbler set" },
    { id = "reset",      name = "RESET",      sub = "progress lost" },
    { id = "fail",       name = "FAIL",       sub = "run over" },
    { id = "handle",     name = "HANDLE",     sub = "win sting hit" },
    { id = "cleared",    name = "CLEARED",    sub = "win sting tail" },
    { id = "start",      name = "START",      sub = "run begins" },
    { id = "footstep",   name = "FOOTSTEP",   sub = "guard" },
    { id = "flashlight", name = "FLASHLIGHT", sub = "blackout" },
    { id = "uiConfirm",  name = "UI CONFIRM", sub = "menu A" },
    { id = "uiBack",     name = "UI BACK",    sub = "menu B" },
    { id = "uiHover",    name = "UI HOVER",   sub = "menu move" },
    { id = "keypadError", name = "KEYPAD ERROR", sub = "wrong arrow" },
    { id = "bgmTitle",   name = "BGM TITLE",  sub = "title bed",  track = "sounds/title" },
    { id = "bgmDefault", name = "BGM RUN",    sub = "default bed", track = "sounds/bgm" },
    { id = "bgmClub",    name = "BGM CLUB",   sub = "too loud",   track = "sounds/nightclub" },
    { id = "bgmNight",   name = "BGM NIGHT",  sub = "guard",      track = "sounds/ambience" },
}

-- Which mix entry owns each bed, so bgmStart only has to name a track.
local TRACK_MIX <const> = {
    ["sounds/title"]     = "bgmTitle",
    ["sounds/bgm"]       = "bgmDefault",
    ["sounds/nightclub"] = "bgmClub",
    ["sounds/ambience"]  = "bgmNight",
}

-- The SDK clips above 1.0 and errors below 0, and the mix is user-editable now.
local function lvl(v)
    if v < 0 then return 0 end
    if v > 1 then return 1 end
    return v
end

local tickSample <const> = snd.sample.new("sounds/tick")
local sweetSample <const> = snd.sample.new("sounds/sweet")
local clearedSample <const> = snd.sample.new("sounds/cleared")
-- DECOY. The curated fake click ends in a 165-305 ms falling midrange buzz.
-- Its odd harmonics distinguish the tail without relying on the original bass
-- dud. Rebuild the complete sample with scripts/build-decoy-sound.py.
local fakeSample <const> = snd.sample.new("sounds/sweet-fake")
local footstepSample <const> = snd.sample.new("sounds/footstep")

-- UI feedback. Split by intent, not by button: confirm is "going in", back is
-- "coming out", hover is the cursor moving between rows.
local uiConfirmVoice = snd.sampleplayer.new("sounds/ui-confirm")
local uiBackVoice = snd.sampleplayer.new("sounds/ui-cancel-back")
local uiHoverVoice = snd.sampleplayer.new("sounds/ui-hover")
local keypadErrorVoice = snd.sampleplayer.new("sounds/keypad-error")

local tickVoices = {}
local tickIdx = 1

for i = 1, 6 do
    tickVoices[i] = snd.sampleplayer.new(tickSample)
end

local sweetVoice = snd.sampleplayer.new(sweetSample)
local grazeVoice = snd.sampleplayer.new(tickSample)
grazeVoice:setRate(0.45)

local clickBody = snd.synth.new(snd.kWaveSquare)
clickBody:setADSR(0, 0.070, 0, 0.045)

local failVoice = snd.synth.new(snd.kWaveSquare)
failVoice:setADSR(0.005, 0.5, 0, 0.3)

local resetVoice = snd.synth.new(snd.kWaveSquare)
resetVoice:setADSR(0, 0.12, 0, 0.08)

local clearedVoice = snd.sampleplayer.new(clearedSample)

local lockedVoice = snd.synth.new(snd.kWaveSquare)
lockedVoice:setADSR(0, 0.09, 0, 0.06)

local fakeVoice = snd.sampleplayer.new(fakeSample)
local footstepVoice = snd.sampleplayer.new(footstepSample)

-- BLACKOUT's opening. Two clicks, 210 ms apart: the switch going down, then the
-- beam catching. main.lua's BLACKOUT_CLICK_MS is that gap, so the cone lands on
-- the second one - retime it if this file is ever replaced.
local flashlightVoice = snd.sampleplayer.new("sounds/flashlight")

-- SCRAMBLED's wrong-direction tell: "it is here, but not this way". Deliberately
-- dull and low so it never reads as a latch. Audio only, by design - a text cue
-- would give the direction away for free (game.md SS12).
local wrongVoice = snd.synth.new(snd.kWaveSine)
wrongVoice:setADSR(0.004, 0.09, 0, 0.06)

-- TOO LOUD ducks every mechanism sound under the music. 1.0 is unmodified.
local mechVol = 1.0
local latchesMuted = false
function Sfx.setMechVolume(v, muteLatches)
    mechVol = v or 1.0
    latchesMuted = muteLatches == true
end

-- The title bed. Its own player, so returning to the title never has to care
-- which of the three run tracks was loaded into `bgm`.
local titleBgm = snd.fileplayer.new("sounds/title")

local bgm = snd.fileplayer.new("sounds/bgm")
local currentTrack = "sounds/bgm"
-- Remembered so the menu can duck and restore without knowing which track this
-- particular run happens to be using.
local bgmVol = Sfx.gain("bgmDefault")
local ducked, dustListening = false, false

local function after(ms, fn)
    playdate.timer.performAfterDelay(ms, fn)
end

-- `speed` is dial units per SECOND (main.lua normalises it, so the tick sounds
-- the same whatever the frame rate). 150/s is the old cap of 3 units/frame.
-- The speed term is a multiplier rather than an addend so that muting the entry
-- actually mutes it; 0.2308 reproduces the original +0.06-at-full-speed curve.
function Sfx.tick(speed)
    local v = tickVoices[tickIdx]
    tickIdx = tickIdx % #tickVoices + 1
    local s = math.min(speed, 150) / 50
    v:setRate(0.94 + s * 0.05 + math.random() * 0.06)
    v:setVolume(lvl(Sfx.gain("tick") * (1 + s * 0.2308) * mechVol))
    v:play(1)
end

function Sfx.uiConfirm()
    uiConfirmVoice:setVolume(Sfx.gain("uiConfirm"))
    uiConfirmVoice:play(1)
end

function Sfx.uiBack()
    uiBackVoice:setVolume(Sfx.gain("uiBack"))
    uiBackVoice:play(1)
end

-- Hover fires on every cursor move, so it sits well under the other two: at full
-- volume a held d-pad turns the menu into a machine gun.
function Sfx.uiHover()
    uiHoverVoice:setVolume(Sfx.gain("uiHover"))
    uiHoverVoice:play(1)
end

-- Dedicated supplied error cue; never a fake latch or a progress-reset sound.
-- The bubble also resets visibly, so TOO LOUD does not hide the mistake.
function Sfx.keypadError()
    keypadErrorVoice:stop()
    keypadErrorVoice:setVolume(Sfx.gain("keypadError"))
    keypadErrorVoice:play(1)
end

function Sfx.sweetSpot()
    -- TOO LOUD confirms hits visually; both latch voices are completely muted.
    if latchesMuted then sweetVoice:stop(); return end
    sweetVoice:setVolume(lvl(Sfx.gain("sweet") * mechVol))
    sweetVoice:setRate(1.0)
    sweetVoice:play(1)
end

-- DECOY's fake latch: click, then buzz. The entire cue follows the latch mute.
function Sfx.decoy()
    if latchesMuted then fakeVoice:stop(); return end
    fakeVoice:setVolume(lvl(Sfx.gain("decoy") * mechVol))
    fakeVoice:setRate(1.0)
    fakeVoice:play(1)
end

function Sfx.graze()
    grazeVoice:setVolume(lvl(Sfx.gain("graze") * mechVol))
    grazeVoice:play(1)
end

function Sfx.wrongDir()
    wrongVoice:playNote(70, lvl(Sfx.gain("wrong") * mechVol), 0.10)
end

-- GUARD. Never ducked: missing it is a hard game over, so it has to be heard
-- over whatever bed is playing.
function Sfx.footstep()
    footstepVoice:setVolume(Sfx.gain("footstep"))
    footstepVoice:play(1)
end

-- Never ducked: it is the run announcing itself, and BLACKOUT is banned with
-- TOO LOUD anyway, so nothing is competing with it.
function Sfx.flashlight()
    flashlightVoice:setVolume(Sfx.gain("flashlight"))
    flashlightVoice:play(1)
end

function Sfx.handle()
    sweetVoice:setVolume(Sfx.gain("handle"))
    sweetVoice:setRate(1.0)
    sweetVoice:play(1)
    after(1000, function()
        clearedVoice:setVolume(Sfx.gain("cleared"))
        clearedVoice:play(1)
    end)
end

function Sfx.locked()
    local v = Sfx.gain("locked")
    lockedVoice:playNote(120, v, 0.07)
    after(60, function() lockedVoice:playNote(84, v * 0.93, 0.10) end)
end

function Sfx.fail()
    local v = Sfx.gain("fail")
    failVoice:playNote(180, v, 0.45)
    after(220, function() failVoice:playNote(140, v, 0.55) end)
    after(520, function() failVoice:playNote(95, v, 0.80) end)
end

function Sfx.reset()
    local v = Sfx.gain("reset")
    -- Shares grazeVoice, so it has to set its own level or it inherits whatever
    -- the last graze left behind.
    grazeVoice:setVolume(v)
    grazeVoice:play(1)
    resetVoice:playNote(260, v, 0.09)
    after(90, function() resetVoice:playNote(165, v, 0.14) end)
end

-- One background track per run, chosen at startGame and never changed: the
-- default bed, TOO LOUD's club track, or GUARD's night ambience. TOO LOUD and
-- GUARD are a banned pair, so two beds can never be asked for at once. The level
-- comes from the mix, keyed off the track, so the debug page owns it too.
function Sfx.bgmStart(track)
    titleBgm:stop()
    bgm:stop()
    track = track or "sounds/bgm"
    if track ~= currentTrack then
        bgm:load(track)
        currentTrack = track
    end
    bgmVol = Sfx.gain(TRACK_MIX[track] or "bgmDefault")
    ducked, dustListening = false, false
    Sfx.applyBgmVolume()
    bgm:play(0)
end

function Sfx.bgmStop()
    bgm:stop()
end

-- The pause menu pushes the run into the background, so its music goes with it.
function Sfx.applyBgmVolume()
    bgm:setVolume(dustListening and 0 or (ducked and bgmVol * 0.28 or bgmVol))
end

function Sfx.bgmDuck(on)
    ducked = on and true or false
    Sfx.applyBgmVolume()
end

function Sfx.dustListening(on)
    dustListening = on and true or false
    Sfx.applyBgmVolume()
end

-- Everything the title screen should sound like. Called on boot and on every
-- route back to the title, so no run's music can survive into it. The title bed
-- loops until startGame stops it, and restarts from the top each time you come
-- back - the track is short enough that resuming mid-phrase would read as a bug.
function Sfx.titleAudio()
    bgm:stop()
    titleBgm:stop()
    titleBgm:setVolume(Sfx.gain("bgmTitle"))
    titleBgm:play(0)
end

function Sfx.start()
    local v = Sfx.gain("start")
    clickBody:playNote(160, v, 0.06)
    after(70, function() clickBody:playNote(220, v, 0.08) end)
end

-- ---------------------------------------------------------------------------
-- Debug audition. The Audio page borrows the whole bus: it stops whatever bed is
-- running so a level is judged on that sound alone, and hands the bed back on
-- the way out. Previews call the real Sfx functions, so what is heard here is
-- exactly what the game will play.

-- Its own player, so auditioning a bed never disturbs which track `bgm` has
-- loaded or what `currentTrack` believes.
local previewBgm = snd.fileplayer.new()
local previewTrack = nil
local auditing = false
local bedWasOn = false

local PREVIEW <const> = {
    tick       = function() Sfx.tick(60) end,
    graze      = function() Sfx.graze() end,
    sweet      = function() Sfx.sweetSpot() end,
    decoy      = function() Sfx.decoy() end,
    wrong      = function() Sfx.wrongDir() end,
    locked     = function() Sfx.locked() end,
    reset      = function() Sfx.reset() end,
    fail       = function() Sfx.fail() end,
    handle     = function() Sfx.handle() end,
    cleared    = function()
        clearedVoice:setVolume(Sfx.gain("cleared"))
        clearedVoice:play(1)
    end,
    start      = function() Sfx.start() end,
    footstep   = function() Sfx.footstep() end,
    flashlight = function() Sfx.flashlight() end,
    uiConfirm  = function() Sfx.uiConfirm() end,
    uiBack     = function() Sfx.uiBack() end,
    uiHover    = function() Sfx.uiHover() end,
    keypadError = function() Sfx.keypadError() end,
}

-- Every one-shot voice, so a retrigger is a clean restart rather than a stack.
local ONESHOTS <const> = {
    sweetVoice, grazeVoice, clearedVoice, fakeVoice, footstepVoice,
    flashlightVoice, uiConfirmVoice, uiBackVoice, uiHoverVoice, keypadErrorVoice,
}

local function silenceOneShots()
    for _, v in ipairs(ONESHOTS) do v:stop() end
    for _, v in ipairs(tickVoices) do v:stop() end
    clickBody:stop()
    failVoice:stop()
    resetVoice:stop()
    lockedVoice:stop()
    wrongVoice:stop()
end

function Sfx.auditionBegin()
    if auditing then return end
    auditing = true
    bedWasOn = bgm:isPlaying() or titleBgm:isPlaying()
    bgm:stop()
    titleBgm:stop()
end

-- Hands the bus back. `bgm` still holds the run's track, so the bed only has to
-- be restarted at whatever volume the menu state says it should be.
function Sfx.auditionEnd()
    if not auditing then return end
    auditing = false
    silenceOneShots()
    previewBgm:stop()
    previewTrack = nil
    if bedWasOn then
        bgmVol = Sfx.gain(TRACK_MIX[currentTrack] or "bgmDefault")
        Sfx.applyBgmVolume()
        bgm:play(0)
    end
end

-- Stop everything the audition started, without giving the bed back.
function Sfx.auditionSilence()
    silenceOneShots()
    previewBgm:stop()
    previewTrack = nil
end

-- Play one mix entry on its own. Beds loop; everything else is a clean retrigger.
function Sfx.audition(entry)
    if entry.track then
        if previewTrack ~= entry.track then
            previewBgm:stop()
            previewBgm:load(entry.track)
            previewTrack = entry.track
            previewBgm:setVolume(Sfx.gain(entry.id))
            previewBgm:play(0)
        else
            previewBgm:setVolume(Sfx.gain(entry.id))
            if not previewBgm:isPlaying() then previewBgm:play(0) end
        end
        return
    end
    previewBgm:stop()
    previewTrack = nil
    silenceOneShots()
    local fn = PREVIEW[entry.id]
    if fn then fn() end
end
