local snd <const> = playdate.sound

Sfx = {}

local tickSample <const> = snd.sample.new("sounds/tick")
local sweetSample <const> = snd.sample.new("sounds/sweet")
local clearedSample <const> = snd.sample.new("sounds/cleared")

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

local bgm = snd.fileplayer.new("sounds/bgm")
bgm:setVolume(0.12)

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
    v:setVolume(0.26 + s * 0.06)
    v:play(1)
end

function Sfx.sweetSpot()
    sweetVoice:setVolume(1.0)
    sweetVoice:setRate(1.0)
    sweetVoice:play(1)
end

function Sfx.graze()
    grazeVoice:play(1)
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

function Sfx.bgmStart()
    bgm:stop()
    bgm:setVolume(0.12)
    bgm:play(0)
end

function Sfx.bgmStop()
    bgm:stop()
end

function Sfx.start()
    clickBody:playNote(160, 0.30, 0.06)
    after(70, function() clickBody:playNote(220, 0.30, 0.08) end)
end
