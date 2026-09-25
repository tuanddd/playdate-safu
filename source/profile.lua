local pd <const> = playdate

Profile = { data = nil }

local FILE <const> = "profile"

local DEFAULTS <const> = {
    tutorialDone = false,
    lifetime = 0,
    best = 0,
    name = "",
    id = "",
    pending = false,
}

local function newId()
    local s, ms = pd.getSecondsSinceEpoch()
    math.randomseed(s * 1000 + ms)
    local t = {}
    for i = 1, 16 do t[i] = string.format("%x", math.random(0, 15)) end
    return table.concat(t)
end

function Profile.save()
    pd.datastore.write(Profile.data, FILE)
end

function Profile.load()
    local d = pd.datastore.read(FILE) or {}
    for k, v in pairs(DEFAULTS) do
        if d[k] == nil then d[k] = v end
    end
    if d.id == "" then d.id = newId() end
    Profile.data = d
    Profile.save()
end

function Profile.crack(streak)
    local d = Profile.data
    d.lifetime = d.lifetime + 1
    if streak > d.best then d.best = streak end
    Profile.save()
end

function Profile.finishTutorial()
    if Profile.data.tutorialDone then return end
    Profile.data.tutorialDone = true
    Profile.save()
end

function Profile.setName(name)
    Profile.data.name = name
    Profile.save()
end

function Profile.setPending(flag)
    if Profile.data.pending == flag then return end
    Profile.data.pending = flag
    Profile.save()
end

function Profile.reset()
    local id = Profile.data.id
    pd.datastore.delete(FILE)
    Profile.data = { id = id }
    pd.datastore.write(Profile.data, FILE)
    Profile.load()
end

Profile.load()
