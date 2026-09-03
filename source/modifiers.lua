-- Safu modifier catalogue — the 12 modifiers of game.md §12, their icons, and the
-- combination rules that decide which triples are legal.
--
-- Data, art, the legality rules, and Mods.buildCfg — which turns a rolled set into
-- the tunables one run plays by. The effects themselves live at their natural
-- call sites in main.lua; nothing here reaches into the game loop.
--
-- Art: 14x14, 1-bit, transparent background. Every icon exists twice —
--   individually at  images/modifiers/<icon>       (Mods.iconImage)
--   as one imagetable images/mod-icons                (Mods.iconImage, cheaper)
-- Both are generated; see images/svg/build-icon-files.js and images/icons-manifest.json.
-- The frame numbers below are the imagetable order and must stay in sync with that
-- manifest — regenerate rather than hand-editing either side.

local gfx <const> = playdate.graphics

Mods = {}

-- Dial units per second. WANDERING's spots may not drift faster than this: the
-- player has to be able to close on a moving target while staying under the
-- latch ceiling (MAX_ENGAGE_SPEED = 25/sec), so the drift gets a fifth of it.
Mods.MAX_DRIFT = 5

Mods.ICON_W = 14
Mods.ICON_H = 14
-- pdc strips the -table-w-h suffix: source/images/mod-icons-table-14-14.png
-- compiles to images/mod-icons.pdt. Do not name it "modifiers" — that collides
-- with the images/modifiers/ folder of individual icons.
Mods.ICON_TABLE = "images/mod-icons"
Mods.ICON_DIR = "images/modifiers/"

-- icon id -> imagetable frame (1-indexed, as imagetable:getImage() wants)
Mods.iconFrames = {
    ["eye-off"] = 1,
    ["music-note"] = 2,
    ["crosshair"] = 3,
    ["oil-slip"] = 4,
    ["goo-drip"] = 5,
    ["both-ways"] = 6,
    ["four-pins"] = 7,
    ["drift-target"] = 8,
    ["twin-marks"] = 9,
    ["skull"] = 10,
    ["peaked-cap"] = 11,
    ["flask"] = 12,
}

-- `sub` is the card's second row, set in Nontendo-Light (13px line box). It wraps
-- to at most 2 lines in the card's 113px column — roughly 34 characters. The same
-- string is used by the pause menu's catalogue.
-- axis and tags are FLAVOUR ONLY — legality is decided per pair below, not by axis
-- (game.md §12, "Modes and combinations").
Mods.list = {
    { id = "blackout",      name = "BLACKOUT",      sub = "The dial is not drawn",     axis = "perception", tags = { "channel" }, icon = "eye-off" },
    { id = "too-loud",      name = "TOO LOUD",      sub = "Ticks buried in noise",    axis = "perception", tags = { "channel" }, icon = "music-note" },
    { id = "hair-trigger",  name = "HAIR TRIGGER",  sub = "Only a crawl will latch",  axis = "motor",      tags = {},            icon = "crosshair" },
    { id = "greased",       name = "GREASED",       sub = "It coasts after you stop",     axis = "motor",      tags = {},            icon = "oil-slip" },
    { id = "sticky",        name = "STICKY",        sub = "Shove it to get moving",     axis = "motor",      tags = {},            icon = "goo-drip" },
    { id = "scrambled",     name = "SCRAMBLED",     sub = "Each turn goes either way",     axis = "memory",     tags = {},            icon = "both-ways" },
    { id = "four-tumblers", name = "FOUR TUMBLERS", sub = "Four spots, not three",   axis = "memory",     tags = { "time" },    icon = "four-pins" },
    -- DRIFT MUST STAY WELL UNDER MAX_ENGAGE_SPEED (25 units/sec, main.lua). A spot
    -- that drifts at or above the speed you are allowed to latch at is literally
    -- uncatchable: closing on it fast enough to keep up is itself a graze.
    -- Mods.MAX_DRIFT is the ceiling the effect must honour.
    { id = "wandering",     name = "WANDERING",     sub = "Spots drift while you idle",   axis = "memory",     tags = {},            icon = "drift-target" },
    { id = "decoy",         name = "DECOY",         sub = "One spot is a lie",   axis = "risk",       tags = {},            icon = "twin-marks" },
    { id = "one-shot",      name = "ONE SHOT",      sub = "A wrong pull ends the run",   axis = "risk",       tags = { "fail" },    icon = "skull" },
    { id = "guard",         name = "GUARD",         sub = "Freeze when you hear steps",   axis = "event",      tags = { "fail" },    icon = "peaked-cap" },
    { id = "nitro",         name = "NITRO",         sub = "Keep the device level",   axis = "body",       tags = { "fail" },    icon = "flask" },
}

Mods.byId = {}
for _, m in ipairs(Mods.list) do Mods.byId[m.id] = m end

local iconTable = nil
local singles = {}

-- The shared imagetable. Prefer this when drawing more than one icon.
function Mods.icons()
    if not iconTable then iconTable = gfx.imagetable.new(Mods.ICON_TABLE) end
    return iconTable
end

-- One icon as an image, by icon id ("crosshair") — from the imagetable.
function Mods.iconImage(iconId)
    local frame = Mods.iconFrames[iconId]
    if not frame then return nil end
    return Mods.icons():getImage(frame)
end

-- One icon loaded from its own file instead of the table. Cached. Use this only
-- when you want the standalone asset; iconImage is cheaper.
function Mods.iconFile(iconId)
    if not singles[iconId] then singles[iconId] = gfx.image.new(Mods.ICON_DIR .. iconId) end
    return singles[iconId]
end

-- Draw a modifier's icon with its top-left at x,y.
function Mods.drawIcon(modId, x, y)
    local m = Mods.byId[modId]
    if not m then return end
    local img = Mods.iconImage(m.icon)
    if img then img:draw(x, y) end
end

-- ---------------------------------------------------------------------------
-- Compatibility. Every pair is classified once; a triple is judged by its three
-- pairs. Any banned pair -> discard. Total weight >= 2 -> HARD. Else NORMAL.
-- Mirrors game.md §12 exactly; change them together.

local function key(a, b)
    if a < b then return a .. "|" .. b end
    return b .. "|" .. a
end

local function pairs_(class, list)
    local t = {}
    for _, p in ipairs(list) do t[key(p[1], p[2])] = class end
    return t
end

Mods.BANNED = "banned"

-- The run is impossible.
local banned = pairs_(Mods.BANNED, {
    { "blackout", "too-loud" },
    { "hair-trigger", "sticky" },
    { "too-loud", "guard" },
    { "blackout", "nitro" },
})

-- Weight 2: two ways to lose instantly in one run.
local hard2 = {
    { "one-shot", "guard" },
    { "one-shot", "nitro" },
    { "guard", "nitro" },
}

-- Weight 1: friction. Needs a second one to make the run hard.
local hard1 = {
    { "blackout", "decoy" },
    { "too-loud", "decoy" },
    { "too-loud", "scrambled" },
    { "too-loud", "hair-trigger" },
    { "blackout", "wandering" },
    { "hair-trigger", "greased" },
    { "sticky", "greased" },
    { "nitro", "greased" },
    { "nitro", "sticky" },
    { "scrambled", "wandering" },
    { "four-tumblers", "wandering" },
    { "four-tumblers", "guard" },
    { "decoy", "one-shot" },
}

local weights = {}
for _, p in ipairs(hard2) do weights[key(p[1], p[2])] = 2 end
for _, p in ipairs(hard1) do weights[key(p[1], p[2])] = 1 end

-- "banned", 2, 1 or 0 for a pair of modifier ids.
function Mods.pairClass(a, b)
    local k = key(a, b)
    if banned[k] then return Mods.BANNED end
    return weights[k] or 0
end

-- Score a set of modifiers (ids or entries). Returns nil if any pair is banned,
-- otherwise total weight and the mode it lands in.
function Mods.score(set)
    local ids = {}
    for i, m in ipairs(set) do ids[i] = type(m) == "table" and m.id or m end
    local total = 0
    for i = 1, #ids do
        for j = i + 1, #ids do
            local c = Mods.pairClass(ids[i], ids[j])
            if c == Mods.BANNED then return nil end
            total = total + c
        end
    end
    return total, (total >= 2) and "hard" or "normal"
end

-- Roll a playable set of `count` modifiers. Returns the set and its mode.
function Mods.roll(count)
    count = count or 3
    for _ = 1, 500 do
        local pool = {}
        for i, m in ipairs(Mods.list) do pool[i] = m end
        for i = #pool, 2, -1 do
            local j = math.random(i)
            pool[i], pool[j] = pool[j], pool[i]
        end
        local pick = table.move(pool, 1, count, 1, {})
        local total, mode = Mods.score(pick)
        if total then return pick, mode end
    end
    return nil
end

-- ---------------------------------------------------------------------------
-- Gameplay configuration for one run.
--
-- Every tunable the modifiers touch lives here, defaulted to the unmodified
-- game, so main.lua reads Run.cfg.x instead of a constant and no effect needs a
-- special case at its call site. Fields the renderer owns (drawDial, showEffects,
-- shake) are set here too, so there is one place to look.

function Mods.buildCfg(mods)
    local c = {
        -- perception - consumed by the renderer, not by the rules
        drawDial = true, showEffects = true, shake = true,
        -- the audio bed: exactly one track per run (game.md, "The audio bed").
        -- TOO LOUD and GUARD are a banned pair, so these can never both apply.
        bgmTrack = "sounds/bgm", bgmVol = 0.12, mechVol = 1.0,
        -- motor
        maxEngage = 25, friction = nil, stiction = 0,
        -- the puzzle
        tumblers = 3, randomDirs = false, drift = 0, decoy = false,
        -- run-ending conditions
        oneShot = false, guard = false, nitro = false,
    }
    local has = {}
    for _, m in ipairs(mods or {}) do has[m.id] = true end

    if has["blackout"] then c.drawDial, c.showEffects, c.shake = false, false, false end
    if has["too-loud"] then c.bgmTrack, c.bgmVol, c.mechVol = "sounds/nightclub", 0.50, 0.18 end
    if has["guard"] then c.bgmTrack, c.bgmVol, c.guard = "sounds/ambience", 0.45, true end
    -- 7.5 units/sec is the old 0.15 per frame at 50 fps, versus a normal 25.
    if has["hair-trigger"] then c.maxEngage = 7.5 end
    if has["greased"] then c.friction = 0.90 end
    -- Below this the dial will not move at all; the held input releases in one
    -- shove. Must stay under maxEngage or the pair is unwinnable - which is why
    -- HAIR TRIGGER + STICKY is banned rather than merely hard.
    if has["sticky"] then c.stiction = 14 end
    if has["scrambled"] then c.randomDirs = true end
    if has["four-tumblers"] then c.tumblers = 4 end
    if has["wandering"] then c.drift = Mods.MAX_DRIFT end
    if has["decoy"] then c.decoy = true end
    if has["one-shot"] then c.oneShot = true end
    if has["nitro"] then c.nitro = true end
    return c
end

-- Required turn direction per tumbler. The classic alternating rhythm unless
-- SCRAMBLED, which rolls each one independently.
function Mods.rollDirs(count, random)
    local d = {}
    for i = 1, count do
        if random then
            d[i] = (math.random(2) == 1) and 1 or -1
        else
            d[i] = (i % 2 == 1) and 1 or -1
        end
    end
    return d
end
