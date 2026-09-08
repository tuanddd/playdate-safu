local gfx <const> = playdate.graphics

-- The first safe coaches live progress. BLACKOUT's instructions stay fixed:
-- changing them on a latch would give the player a visual way to count it.
Tutorial = { issue = nil, images = {} }

local prompts <const> = {
    { "FIND A SWEET SPOT", "Turn clockwise slowly.\nWhen the dial shakes\nwith a loud click,\nyou found a sweet spot.\nFind 3 to open the safe." },
    { "NICE! ONE FOUND", "Turn counterclockwise\nslowly this time.\nThe next loud click\nmeans you found\nanother sweet spot." },
    { "ONE MORE TO GO", "Turn clockwise again.\nKeep it slow.\nListen for one last\nloud click." },
    { "YOU FOUND ALL 3!", "Stop turning the crank.\nPress A to open\nthe safe." },
    slow = { "TRY A SLOWER TURN", "That turn was too fast.\nYour progress is reset.\nTry turning clockwise\nmore slowly." },
    reset = { "EASY DOES IT", "Turning too fast makes\nyou start over.\nTurn clockwise slowly\nto find the first spot." },
    locked = { "NOT READY YET", "Opening too soon\nresets your progress.\nFind all 3 spots first.\nStart again by turning\nclockwise slowly." },
}

function Tutorial.reset()
    Tutorial.issue = nil
end

function Tutorial.feedback(step, issue)
    if step == 1 then Tutorial.issue = issue end
end

function Tutorial.draw(step, tumbler, x, y, w, h, gap)
    -- Both lessons use one fixed layout. Every error has already reset the real
    -- tumbler to 1 before drawing, so an error key always carries zero latches.
    local key = step == 2 and "blackout" or (Tutorial.issue or tumbler)
    local img = Tutorial.images[key]
    if not img then
        local fullH = h + gap * 2
        img = gfx.image.new(w + 4, fullH + 4)
        gfx.pushContext(img)
            gfx.setImageDrawMode(gfx.kDrawModeCopy)
            gfx.clearStencil()
            if step == 2 then
                local mod = Mods.byId.blackout
                Art.drawModCard(0, 0, w, h, Mods.iconImage(mod.icon), mod.name, mod.sub)
                Art.drawPlate(0, gap, w, h + gap)
                gfx.setFont(Art.titleFont)
                gfx.drawText("TUTORIAL 2/2", 10, gap + 10)
                gfx.drawLine(10, gap + 28, w - 10, gap + 28)
                gfx.setFont(Art.subFont)
                gfx.drawText("Turn clockwise slowly.\nAfter clicks 1 and 2,\nturn the other way.\nOn click 3, press A.\nIf progress resets,\nstart clockwise again.", 10, gap + 36)
            else
                local prompt = prompts[key]
                Art.drawPlate(0, 0, w, fullH)
                gfx.setFont(Art.titleFont)
                gfx.drawText("TUTORIAL 1/2", 10, 10)
                gfx.drawLine(10, 29, w - 10, 29)
                gfx.drawText(prompt[1], 10, 42)
                gfx.setFont(Art.subFont)
                gfx.drawText(prompt[2], 10, 66)
                gfx.drawLine(10, fullH - 49, w - 10, fullH - 49)
                gfx.setFont(Art.titleFont)
                gfx.drawText(string.format("%d / 3 SPOTS FOUND", tumbler - 1), 10, fullH - 39)
                gfx.setFont(Art.subFont)
                gfx.drawText("No timer. Take your time.", 10, fullH - 21)
            end
        gfx.popContext()
        Tutorial.images[key] = img
    end
    img:draw(x, y)
end
