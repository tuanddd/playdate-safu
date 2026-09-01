local ENABLED <const> = false

if not ENABLED or not playdate.isSimulator then return end

local pd <const> = playdate
local gfx <const> = pd.graphics
local base = pd.update
local out <const> = "/private/tmp/claude-501/-Users-vincent-Desktop-work-playdate-test-safu/12d0067b-cb33-4ea5-ab74-d0654a6bea0d/scratchpad/shots/"
playdate.isCrankDocked = function() return false end

local frame = 0
local shotAt = {}
local lastTumbler = 1
local n = 0

local function save(name)
    pd.simulator.writeToFile(gfx.getDisplayImage(), out .. name .. ".png")
end

function pd.update()
    frame = frame + 1
    if frame == 4 then Sim.setCrank(1.6) end
    if frame == 12 then Sim.start(); Sim.fps() end
    if frame == 14 then Sim.setCrank(1.6 * Sim.need()) end

    base()

    if frame == 3 then save("01-title") end
    if frame == 30 then save("02-play") end
    if frame == 160 then save("07-fps") end
    if Sim.tumbler() ~= lastTumbler then
        lastTumbler = Sim.tumbler()
        n = n + 1
        shotAt[frame + 12] = "03-hit" .. n
        if lastTumbler <= 3 then
            Sim.setCrank(1.6 * Sim.need())
        else
            Sim.setCrank(0)
            shotAt[frame + 40] = "03-allfound"
            shotAt.pull = frame + 45
        end
    end
    if shotAt.pull and frame == shotAt.pull then Sim.handle() end
    if shotAt[frame] then save(shotAt[frame]) end
    if Sim.state() == 3 then
        if not shotAt.win then
            shotAt.win = frame
        end
        local d = frame - shotAt.win
        if d == 30 then save("04-door") end
        if d == 105 then save("05-win") end
        if d == 125 and not shotAt.lose then
            shotAt.lose = frame
            Sim.start()
            Sim.setRemaining(400)
            Sim.setCrank(1.2)
        end
    end
    if shotAt.lose and frame == shotAt.lose + 60 then
        save("06-lose")
        pd.simulator.exit()
    end
    if frame > 1500 then pd.simulator.exit() end
end
