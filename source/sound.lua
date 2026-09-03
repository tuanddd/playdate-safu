local snd <const> = playdate.sound

Sfx = {}

local tickSample <const> = snd.sample.new("sounds/tick")
local sweetSample <const> = snd.sample.new("sounds/sweet")
local clearedSample <const> = snd.sample.new("sounds/cleared")
-- DECOY. Same attack as sweet, with a 92 Hz dud in the tail from 105 ms. The
-- separation in the 80-110 Hz band is the whole tell; see game.md, "Measured
-- audio headroom", before retuning either file.
local fakeSample <const> = snd.sample.new("sounds/sweet-fake")
local footstepSample <const> = snd.sample.new("sounds/footstep")

-- UI feedback. Split by intent, not by button: confirm is "going in", back is
-- "coming out", hover is the cursor moving between rows.
local uiConfirmVoice = snd.sampleplayer.new("sounds/ui-confirm")
local uiBackVoice = snd.sampleplayer.new("sounds/ui-cancel-back")
local uiHoverVoice = snd.sampleplayer.new("sounds/ui-hover")

local tickVoices = {}
local tickIdx = 1

for i = 1, 6 do
    tickVoices[i] = snd.sampleplayer.new(tickSample)
end

local sweetVoice = snd.sampleplayer.new(sweetSample)
local grazeVoice = snd.sampleplayer.new(tickSample)
grazeVoice:setRate(0.45)
grazeVoice:setVolume(0.5)

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
function Sfx.setMechVolume(v) mechVol = v or 1.0 end

-- The title bed. Its own player, so returning to the title never has to care
-- which of the three run tracks was loaded into `bgm`.
local titleBgm = snd.fileplayer.new("sounds/title")
local titleVol <const> = 0.35
titleBgm:setVolume(titleVol)

local bgm = snd.fileplayer.new("sounds/bgm")
bgm:setVolume(0.12)
local currentTrack = "sounds/bgm"
-- Remembered so the menu can duck and restore without knowing which track or
-- volume this particular run happens to be using.
local bgmVol = 0.12

local function after(ms, fn)
    playdate.timer.performAfterDelay(ms, fn)
end

-- `speed` is dial units per SECOND (main.lua normalises it, so the tick sounds
-- the same whatever the frame rate). 150/s is the old cap of 3 units/frame.
function Sfx.tick(speed)
    local v = tickVoices[tickIdx]
    tickIdx = tickIdx % #tickVoices + 1
    local s = math.min(speed, 150) / 50
    v:setRate(0.94 + s * 0.05 + math.random() * 0.06)
    v:setVolume((0.26 + s * 0.06) * mechVol)
    v:play(1)
end

function Sfx.uiConfirm()
    if uiConfirmVoice then uiConfirmVoice:play(1) end
end

function Sfx.uiBack()
    if uiBackVoice then uiBackVoice:play(1) end
end

-- Hover fires on every cursor move, so it sits well under the other two: at full
-- volume a held d-pad turns the menu into a machine gun.
function Sfx.uiHover()
    if uiHoverVoice then
        uiHoverVoice:setVolume(0.45)
        uiHoverVoice:play(1)
    end
end

function Sfx.sweetSpot()
    -- Ducked less than the ticks under TOO LOUD: a real latch still has to cut
    -- through the music or the run is unreadable.
    sweetVoice:setVolume(math.max(mechVol, 0.35))
    sweetVoice:setRate(1.0)
    sweetVoice:play(1)
end

-- DECOY's fake latch. Same level as the real one; only the tail differs.
function Sfx.decoy()
    fakeVoice:setVolume(math.max(mechVol, 0.35))
    fakeVoice:setRate(1.0)
    fakeVoice:play(1)
end

function Sfx.graze()
    grazeVoice:setVolume(0.5 * mechVol)
    grazeVoice:play(1)
end

function Sfx.wrongDir()
    wrongVoice:playNote(70, 0.16 * mechVol, 0.10)
end

-- GUARD. Never ducked: missing it is a hard game over, so it has to be heard
-- over whatever bed is playing.
function Sfx.footstep()
    footstepVoice:setVolume(1.0)
    footstepVoice:play(1)
end

-- Never ducked: it is the run announcing itself, and BLACKOUT is banned with
-- TOO LOUD anyway, so nothing is competing with it.
function Sfx.flashlight()
    flashlightVoice:setVolume(1.0)
    flashlightVoice:play(1)
end

function Sfx.handle()
    sweetVoice:setVolume(1.0)
    sweetVoice:setRate(1.0)
    sweetVoice:play(1)
    after(1000, function()
        clearedVoice:setVolume(0.45)
        clearedVoice:play(1)
    end)
end

function Sfx.locked()
    lockedVoice:playNote(120, 0.30, 0.07)
    after(60, function() lockedVoice:playNote(84, 0.28, 0.10) end)
end

function Sfx.fail()
    failVoice:playNote(180, 0.30, 0.45)
    after(220, function() failVoice:playNote(140, 0.30, 0.55) end)
    after(520, function() failVoice:playNote(95, 0.30, 0.80) end)
end

function Sfx.reset()
    grazeVoice:play(1)
    resetVoice:playNote(260, 0.26, 0.09)
    after(90, function() resetVoice:playNote(165, 0.26, 0.14) end)
end

-- One background track per run, chosen at startGame and never changed: the
-- default bed, TOO LOUD's club track, or GUARD's night ambience. TOO LOUD and
-- GUARD are a banned pair, so two beds can never be asked for at once.
function Sfx.bgmStart(track, vol)
    titleBgm:stop()
    bgm:stop()
    if track and track ~= currentTrack then
        bgm:load(track)
        currentTrack = track
    end
    bgmVol = vol or 0.12
    bgm:setVolume(bgmVol)
    bgm:play(0)
end

function Sfx.bgmStop()
    bgm:stop()
end

-- The pause menu pushes the run into the background, so its music goes with it.
function Sfx.bgmDuck(on)
    bgm:setVolume(on and bgmVol * 0.28 or bgmVol)
end

-- Everything the title screen should sound like. Called on boot and on every
-- route back to the title, so no run's music can survive into it. The title bed
-- loops until startGame stops it, and restarts from the top each time you come
-- back - the track is short enough that resuming mid-phrase would read as a bug.
function Sfx.titleAudio()
    bgm:stop()
    titleBgm:stop()
    titleBgm:setVolume(titleVol)
    titleBgm:play(0)
end

function Sfx.start()
    clickBody:playNote(160, 0.30, 0.06)
    after(70, function() clickBody:playNote(220, 0.30, 0.08) end)
end
