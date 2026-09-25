const BOARD_KEY = "board";
const LIST_KEEP = 50;
const LIST_SHOW = 10;
const RATE_LIMIT_MS = 5000;
const MAX_SCORE = 99999;
const MAX_BODY_BYTES = 1024;
const ID_PATTERN = /^[0-9a-f]{16}$/;
const NAME_PATTERN = /^[A-Za-z0-9 ._-]{1,10}$/;

const encoder = new TextEncoder();

function json(status, data) {
  const bytes = encoder.encode(JSON.stringify(data));
  return new Response(bytes, {
    status,
    headers: {
      "Content-Type": "application/json",
      "Content-Length": String(bytes.byteLength),
      "Cache-Control": "no-store, no-transform",
    },
  });
}

function fail(status, error) {
  return json(status, { error });
}

async function loadBoard(env) {
  const board = await env.SCORES.get(BOARD_KEY, "json");
  if (!board || !Array.isArray(board.streak) || !Array.isArray(board.lifetime)) {
    return { updated: 0, streak: [], lifetime: [] };
  }
  return board;
}

function publicRows(list, viewerId) {
  return list.slice(0, LIST_SHOW).map((entry) =>
    entry.id === viewerId
      ? { name: entry.name, score: entry.score, me: true }
      : { name: entry.name, score: entry.score },
  );
}

function viewerRanks(board, viewerId) {
  const you = {};
  for (const list of ["streak", "lifetime"]) {
    const index = board[list].findIndex((entry) => entry.id === viewerId);
    if (index >= LIST_SHOW) you[list] = { rank: index + 1, score: board[list][index].score };
  }
  return Object.keys(you).length > 0 ? you : null;
}

function publicBoard(board, viewerId) {
  const result = {
    streak: publicRows(board.streak, viewerId),
    lifetime: publicRows(board.lifetime, viewerId),
    updated: board.updated || 0,
  };
  const you = viewerId ? viewerRanks(board, viewerId) : null;
  if (you) result.you = you;
  return result;
}

function compareEntries(a, b) {
  if (a.score !== b.score) return b.score - a.score;
  if (a.ts !== b.ts) return a.ts - b.ts;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

function upsert(list, id, name, score, now) {
  const previous = list.find((entry) => entry.id === id);
  const next = list.filter((entry) => entry.id !== id);
  if (score > 0) {
    const ts = previous && previous.score === score ? previous.ts : now;
    next.push({ id, name, score, ts });
  }
  next.sort(compareEntries);
  return next.slice(0, LIST_KEEP);
}

function isScore(value) {
  return Number.isInteger(value) && value >= 0 && value <= MAX_SCORE;
}

function parseSubmission(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return { error: "body must be a JSON object" };
  }
  const { id, name, best, lifetime } = body;
  if (typeof id !== "string" || !ID_PATTERN.test(id)) {
    return { error: "id must be 16 lowercase hex chars" };
  }
  const trimmed = typeof name === "string" ? name.trim() : "";
  if (!NAME_PATTERN.test(trimmed)) {
    return { error: "name must be 1-10 chars of A-Z 0-9 space . - _" };
  }
  if (!isScore(best)) return { error: "best must be an integer 0-99999" };
  if (!isScore(lifetime)) return { error: "lifetime must be an integer 0-99999" };
  if (best > lifetime) return { error: "best cannot exceed lifetime" };
  return { value: { id, name: trimmed.toUpperCase(), best, lifetime } };
}

async function handlePost(request, env, playerHeader) {
  if (Number(request.headers.get("Content-Length") || 0) > MAX_BODY_BYTES) {
    return fail(400, "body too large");
  }
  const text = await request.text();
  if (encoder.encode(text).byteLength > MAX_BODY_BYTES) return fail(400, "body too large");

  let body;
  try {
    body = JSON.parse(text);
  } catch {
    return fail(400, "invalid json");
  }

  const parsed = parseSubmission(body);
  if (parsed.error) return fail(400, parsed.error);
  const submission = parsed.value;
  if (playerHeader !== null && playerHeader !== submission.id) {
    return fail(400, "X-Safu-Player does not match id");
  }

  const playerKey = `p:${submission.id}`;
  const now = Date.now();
  const [record, board] = await Promise.all([
    env.SCORES.get(playerKey, "json"),
    loadBoard(env),
  ]);

  if (record && now - record.ts < RATE_LIMIT_MS) {
    return fail(429, "too many requests, wait 5 seconds");
  }

  const merged = {
    name: submission.name,
    best: Math.max(record?.best ?? 0, submission.best),
    lifetime: Math.max(record?.lifetime ?? 0, submission.lifetime),
    ts: now,
  };

  const nextBoard = {
    updated: board.updated || 0,
    streak: upsert(board.streak, submission.id, merged.name, merged.best, now),
    lifetime: upsert(board.lifetime, submission.id, merged.name, merged.lifetime, now),
  };

  const changed =
    JSON.stringify([nextBoard.streak, nextBoard.lifetime]) !==
    JSON.stringify([board.streak, board.lifetime]);
  if (changed) {
    nextBoard.updated = Math.floor(now / 1000);
    await env.SCORES.put(BOARD_KEY, JSON.stringify(nextBoard));
  }
  await env.SCORES.put(playerKey, JSON.stringify(merged));

  return json(200, publicBoard(nextBoard, submission.id));
}

export default {
  async fetch(request, env) {
    try {
      if (request.headers.get("X-Safu-Client") !== "1") return fail(403, "forbidden");

      const { pathname } = new URL(request.url);
      if (pathname === "/scores" || pathname === "/scores/") {
        if (request.method === "GET" || request.method === "POST") {
          const playerHeader = request.headers.get("X-Safu-Player");
          if (playerHeader !== null && !ID_PATTERN.test(playerHeader)) {
            return fail(400, "X-Safu-Player must be 16 lowercase hex chars");
          }
          if (request.method === "GET") {
            return json(200, publicBoard(await loadBoard(env), playerHeader));
          }
          return await handlePost(request, env, playerHeader);
        }
      }
      return fail(404, "not found");
    } catch {
      return fail(500, "server error");
    }
  },
};
