-- One automatic gear to catch per real sweet spot. Timing uses play time, so
-- the gear and its feedback freeze along with the run when paused or docked.
GearMesh = {
    SPEED = 120,         -- clockwise degrees/sec: one revolution every 3 seconds
    CATCH_HALF = 12,      -- 200 ms total catch window, centered on twelve o'clock
    GAP_HALF = 18,        -- visual notch includes room for the catch's width
    CAUGHT_MS = 500,
    MISS_MS = 650,
}

function GearMesh.reset()
    GearMesh.active = false
    GearMesh.angle = 180
    GearMesh.caughtMs = 0
    GearMesh.missMs = 0
    GearMesh.waitForRelease = false
    GearMesh.blockOpen = false
end

function GearMesh.cancel()
    GearMesh.active = false
    GearMesh.caughtMs = 0
    GearMesh.missMs = 0
    GearMesh.waitForRelease = false
    -- Preserve blockOpen: a cancelled catch cannot become a handle pull.
end

function GearMesh.begin()
    GearMesh.active = true
    GearMesh.angle = math.random(120, 240)
    GearMesh.caughtMs = 0
    GearMesh.missMs = 0
    GearMesh.waitForRelease = true
    GearMesh.blockOpen = true
end

function GearMesh.visible()
    return GearMesh.active or GearMesh.caughtMs > 0
end

function GearMesh.update(dt)
    if GearMesh.active then
        GearMesh.angle = (GearMesh.angle + GearMesh.SPEED * dt / 1000) % 360
        GearMesh.missMs = math.max(0, GearMesh.missMs - dt)
    else
        GearMesh.caughtMs = math.max(0, GearMesh.caughtMs - dt)
    end
end

function GearMesh.press()
    if not GearMesh.active or GearMesh.waitForRelease then return nil end
    local distance = math.abs((GearMesh.angle + 180) % 360 - 180)
    if distance <= GearMesh.CATCH_HALF then
        GearMesh.active = false
        GearMesh.angle = 0
        GearMesh.missMs = 0
        GearMesh.caughtMs = GearMesh.CAUGHT_MS
        return "caught"
    end
    GearMesh.missMs = GearMesh.MISS_MS
    return "miss"
end

function GearMesh.visualState()
    if GearMesh.caughtMs > 0 then return "caught" end
    return GearMesh.missMs > 0 and "miss" or "spinning"
end

GearMesh.reset()
