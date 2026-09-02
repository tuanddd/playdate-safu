-- Safu modifier catalogue — the 12 modifiers of game.md §12, their icons, and the
-- combination rules that decide which triples are legal.
--
-- DATA AND ART ONLY. No modifier mechanic is implemented; nothing here changes the
-- game yet. It exists so the HUD and the roll logic have one place to read from.
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

-- `sub` is the card's second row, set in Roobert-11-Medium. That face has a 22px
-- line box and the card only has ~41px under the title, so a subtitle must fit
-- on ONE line of the 113px column — about 14 characters. Longer text clips.
-- axis and tags are FLAVOUR ONLY — legality is decided per pair below, not by axis
-- (game.md §12, "Modes and combinations").
Mods.list = {
    { id = "blackout",      name = "BLACKOUT",      sub = "No dial",     axis = "perception", tags = { "channel" }, icon = "eye-off" },
    { id = "too-loud",      name = "TOO LOUD",      sub = "Ticks buried",    axis = "perception", tags = { "channel" }, icon = "music-note" },
    { id = "hair-trigger",  name = "HAIR TRIGGER",  sub = "Crawl only",  axis = "motor",      tags = {},            icon = "crosshair" },
    { id = "greased",       name = "GREASED",       sub = "It coasts",     axis = "motor",      tags = {},            icon = "oil-slip" },
    { id = "sticky",        name = "STICKY",        sub = "Shove it",     axis = "motor",      tags = {},            icon = "goo-drip" },
    { id = "scrambled",     name = "SCRAMBLED",     sub = "Random turn",     axis = "memory",     tags = {},            icon = "both-ways" },
    { id = "four-tumblers", name = "FOUR TUMBLERS", sub = "Four spots",   axis = "memory",     tags = { "time" },    icon = "four-pins" },
    -- DRIFT MUST STAY WELL UNDER MAX_ENGAGE_SPEED (25 units/sec, main.lua). A spot
    -- that drifts at or above the speed you are allowed to latch at is literally
    -- uncatchable: closing on it fast enough to keep up is itself a graze.
    -- Mods.MAX_DRIFT is the ceiling the effect must honour.
    { id = "wandering",     name = "WANDERING",     sub = "Spots drift",   axis = "memory",     tags = {},            icon = "drift-target" },
    { id = "decoy",         name = "DECOY",         sub = "One is fake",   axis = "risk",       tags = {},            icon = "twin-marks" },
    { id = "one-shot",      name = "ONE SHOT",      sub = "One try",   axis = "risk",       tags = { "fail" },    icon = "skull" },
    { id = "guard",         name = "GUARD",         sub = "Stop moving",   axis = "event",      tags = { "fail" },    icon = "peaked-cap" },
    { id = "nitro",         name = "NITRO",         sub = "Keep it level",   axis = "body",       tags = { "fail" },    icon = "flask" },
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
