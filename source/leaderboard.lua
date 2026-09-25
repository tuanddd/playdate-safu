local pd <const> = playdate
local gfx <const> = playdate.graphics

Board = {
    HOST = nil,
    PORT = 443,
    SSL = true,
    REASON = "Share your Safu scores on the online standings.",
    TIMEOUT_MS = 15000,
    page = 1,
    list = pd.datastore.read("board"),
    status = "idle",
    want = nil,
    conn = nil,
    method = nil,
    sentAt = 0,
}

local PAGES <const> = {
    { key = "streak", title = "BEST STREAK", mine = "best", art = "images/standings-streak" },
    { key = "lifetime", title = "BEST TOTAL", mine = "lifetime", art = "images/standings-total" },
}

local STATUS_TEXT <const> = {
    idle = "",
    loading = "UPDATING...",
    sending = "SENDING SCORE...",
    ok = "ONLINE",
    sent = "SCORE SENT!",
    off = "ONLINE BOARD IS OFF",
    denied = "NETWORK NOT ALLOWED",
    offline = "OFFLINE - LAST SAVED BOARD",
    pending = "NOT SENT - WILL RETRY LATER",
    rejected = "SCORE REJECTED",
    wait = "TOO FAST - TRY AGAIN SOON",
    empty = "CRACK A SAFE FIRST",
}

local ROWS <const> = 8
local ROW_Y <const> = 68
local ROW_H <const> = 20
local ROW_L <const>, ROW_R <const> = 20, 380

local plates = {}

local function plate(page)
    if plates[page.art] == nil then
        plates[page.art] = playdate.file.exists(page.art .. ".pdi")
            and gfx.image.new(page.art) or false
    end
    return plates[page.art]
end

function Board.statusText()
    return STATUS_TEXT[Board.status] or ""
end

function Board.refresh()
    Board.want = { method = "GET" }
end

function Board.submit()
    Profile.setPending(true)
    Board.want = { method = "POST" }
end

local function closeConn()
    local c = Board.conn
    Board.conn = nil
    if c then c:close() end
end

local function fail(code)
    if Board.method == "POST" then
        if code == 400 then
            Profile.setPending(false)
            Board.status = "rejected"
        else
            Board.status = code == 429 and "wait" or "pending"
        end
    else
        Board.status = "offline"
    end
end

local function onComplete()
    local c = Board.conn
    if not c then return end
    local code = c:getResponseStatus()
    local chunks = {}
    local n = c:getBytesAvailable()
    while n and n > 0 do
        chunks[#chunks + 1] = c:read(n)
        n = c:getBytesAvailable()
    end
    closeConn()
    if code == 200 then
        local data = json.decode(table.concat(chunks))
        if data and data.streak and data.lifetime then
            Board.list = data
            pd.datastore.write(data, "board")
            if Board.method == "POST" then
                Profile.setPending(false)
                Board.status = "sent"
            else
                Board.status = "ok"
            end
            return
        end
    end
    fail(code)
end

function Board.busy()
    return Board.conn ~= nil
end

function Board.update()
    if Board.conn and pd.getCurrentTimeMilliseconds() - Board.sentAt > Board.TIMEOUT_MS then
        closeConn()
        fail()
    end
    if Board.conn or not Board.want then return end
    local req = Board.want
    Board.want = nil
    Board.method = req.method
    if not Board.HOST or not pd.network then
        Board.status = "off"
        return
    end
    local made, conn = pcall(pd.network.http.new, Board.HOST, Board.PORT, Board.SSL, Board.REASON)
    if not made or not conn then
        Board.status = "denied"
        return
    end
    conn:setConnectTimeout(10)
    conn:setRequestCompleteCallback(onComplete)
    conn:setConnectionClosedCallback(function()
        if Board.conn == conn then
            closeConn()
            fail()
        end
    end)
    Board.conn = conn
    Board.sentAt = pd.getCurrentTimeMilliseconds()
    Board.status = req.method == "POST" and "sending" or "loading"
    local headers = {
        ["X-Safu-Client"] = "1",
        ["X-Safu-Player"] = Profile.data.id,
        ["Content-Type"] = "application/json",
    }
    local sent, queued
    if req.method == "POST" then
        local d = Profile.data
        local body = json.encode({ id = d.id, name = d.name, best = d.best, lifetime = d.lifetime })
        sent, queued = pcall(conn.post, conn, "/scores", headers, body)
    else
        sent, queued = pcall(conn.get, conn, "/scores", headers)
    end
    if not sent or not queued then
        closeConn()
        fail()
    end
end

function Board.open()
    Board.page = 1
    if Profile.data.pending and Profile.data.name ~= "" then
        Board.want = { method = "POST" }
    else
        Board.refresh()
    end
end

function Board.input()
    if pd.buttonJustPressed(pd.kButtonLeft) or pd.buttonJustPressed(pd.kButtonRight) then
        Board.page = Board.page % #PAGES + 1
        Sfx.uiHover()
    elseif pd.buttonJustPressed(pd.kButtonA) then
        Sfx.uiConfirm()
        Board.refresh()
    elseif pd.buttonJustPressed(pd.kButtonB) then
        Sfx.uiBack()
        return true
    end
    return false
end

local function drawRow(i, rank, name, score, mine)
    local y = ROW_Y + (i - 1) * ROW_H
    local font = Art.numFont
    local inkTop, inkH = Art.inkBand(font, Art.CAPS)
    local ty = y + (ROW_H - inkH) // 2 - inkTop
    if mine then
        gfx.setColor(gfx.kColorWhite)
        gfx.fillRoundRect(ROW_L - 2, y + 1, ROW_R - ROW_L + 4, ROW_H - 2, 3)
        gfx.setImageDrawMode(gfx.kDrawModeFillBlack)
    else
        gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    end
    gfx.setFont(font)
    gfx.drawTextAligned(rank, ROW_L + 18, ty, kTextAlignment.right)
    local nx = ROW_L + 30
    gfx.drawText(name, nx, ty)
    local scoreText = string.format("%02d", score)
    local sw = font:getTextWidth(scoreText)
    gfx.drawText(scoreText, ROW_R - 4 - sw, ty)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    gfx.setColor(mine and gfx.kColorBlack or gfx.kColorWhite)
    local dotY = y + ROW_H // 2 + 3
    for x = nx + font:getTextWidth(name) + 6, ROW_R - 10 - sw, 4 do
        gfx.fillRect(x, dotY, 2, 2)
    end
    gfx.setColor(gfx.kColorBlack)
end

function Board.draw()
    local page = PAGES[Board.page]
    local bg = plate(page)
    if bg then
        bg:draw(0, 0)
    else
        gfx.clear(gfx.kColorBlack)
    end
    local d = Profile.data

    gfx.setFont(Art.titleFont)
    gfx.setImageDrawMode(gfx.kDrawModeFillBlack)
    local inkTop, inkH = Art.inkBand(Art.titleFont, Art.CAPS)
    gfx.drawTextAligned(page.title, 200, 53 - inkH // 2 - inkTop, kTextAlignment.center)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
    local half = Art.titleFont:getTextWidth(page.title) // 2 + 12
    gfx.setColor(gfx.kColorBlack)
    gfx.fillTriangle(200 - half, 53, 200 - half + 6, 49, 200 - half + 6, 57)
    gfx.fillTriangle(200 + half, 53, 200 + half - 6, 49, 200 + half - 6, 57)

    local entries = Board.list and Board.list[page.key] or {}
    local shownMine = false
    local row = 0
    for i = 1, math.min(#entries, ROWS) do
        local e = entries[i]
        local mine = e.me == true
        if mine then shownMine = true end
        row = row + 1
        drawRow(row, tostring(i), e.name or "?", e.score or 0, mine)
    end
    local myScore = d[page.mine]
    if not shownMine and myScore > 0 then
        local you = Board.list and Board.list.you and Board.list.you[page.key]
        row = math.min(row + 1, ROWS)
        drawRow(row, you and tostring(you.rank) or "-", d.name ~= "" and d.name or "YOU",
            you and you.score or myScore, true)
    end
    if row == 0 then
        gfx.setFont(Art.numFont)
        gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
        gfx.drawTextAligned("NO SCORES YET", 200, ROW_Y + 60, kTextAlignment.center)
        gfx.setImageDrawMode(gfx.kDrawModeCopy)
    end

    gfx.setFont(Art.subFont)
    gfx.setImageDrawMode(gfx.kDrawModeFillWhite)
    gfx.drawText(Board.statusText(), ROW_L, 228)
    gfx.drawTextAligned("A REFRESH   B BACK", ROW_R, 228, kTextAlignment.right)
    gfx.setImageDrawMode(gfx.kDrawModeCopy)
end
