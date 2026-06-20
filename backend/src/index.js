/* Character Studio backend — Cloudflare Worker + D1.
   Username/password auth (PBKDF2 + DB-backed session tokens) and a
   whole-blob progress sync endpoint mirroring the frontend's localStorage shape. */

const SESSION_COOKIE = "studio_session";
const DEFAULT_SESSION_TTL_DAYS = 30;
const PBKDF2_ITERATIONS = 100000;

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGIN || "").split(",").map((s) => s.trim()).filter(Boolean);
  const allowOrigin = allowed.includes(origin) ? origin : allowed[0] || "";
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}

function json(data, status, extraHeaders) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: Object.assign({ "Content-Type": "application/json" }, extraHeaders || {}),
  });
}

function bufToHex(buf) {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function hexToBuf(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  return bytes;
}

function randomHex(byteLen) {
  const bytes = new Uint8Array(byteLen);
  crypto.getRandomValues(bytes);
  return bufToHex(bytes.buffer);
}

async function hashPassword(password, saltHex) {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const derived = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: hexToBuf(saltHex), iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    keyMaterial,
    256
  );
  return bufToHex(derived);
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function parseCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  const match = header.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[1]) : null;
}

function sessionCookieHeader(token, maxAgeSeconds) {
  const parts = [
    SESSION_COOKIE + "=" + encodeURIComponent(token),
    "Path=/",
    "HttpOnly",
    "Secure",
    "SameSite=None",
    "Max-Age=" + maxAgeSeconds,
  ];
  return parts.join("; ");
}

function clearCookieHeader() {
  return SESSION_COOKIE + "=; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=0";
}

async function getSessionUser(request, env) {
  const token = parseCookie(request, SESSION_COOKIE);
  if (!token) return null;
  const row = await env.DB.prepare(
    "SELECT u.id, u.username, u.class_name, u.role FROM sessions s JOIN users u ON u.id = s.user_id " +
      "WHERE s.token = ? AND s.expires_at > datetime('now')"
  )
    .bind(token)
    .first();
  return row || null;
}

function isValidUsername(u) {
  return typeof u === "string" && /^[A-Za-z0-9_.-]{3,32}$/.test(u);
}

async function handleSignup(request, env) {
  const body = await request.json().catch(() => ({}));
  const username = (body.username || "").trim();
  const password = body.password || "";
  const className = (body.class_name || "").trim().slice(0, 64) || null;

  if (!isValidUsername(username)) {
    return json({ error: "Username must be 3-32 characters: letters, numbers, _ . -" }, 400);
  }
  if (typeof password !== "string" || password.length < 6) {
    return json({ error: "Password must be at least 6 characters." }, 400);
  }
  if (body.parent_consent !== true) {
    return json({ error: "A parent or guardian must consent before creating a student account." }, 400);
  }

  const existing = await env.DB.prepare("SELECT id FROM users WHERE username = ?").bind(username).first();
  if (existing) return json({ error: "That username is already taken." }, 409);

  const salt = randomHex(16);
  const hash = await hashPassword(password, salt);
  const inserted = await env.DB.prepare(
    "INSERT INTO users (username, password_hash, salt, class_name, parent_consent_at) VALUES (?, ?, ?, ?, datetime('now')) RETURNING id"
  )
    .bind(username, hash, salt, className)
    .first();
  const userId = inserted.id;
  await env.DB.prepare("INSERT INTO progress (user_id, data) VALUES (?, '{}')").bind(userId).run();

  return startSession(env, userId, { id: userId, username, class_name: className, role: "student" });
}

async function handleLogin(request, env) {
  const body = await request.json().catch(() => ({}));
  const username = (body.username || "").trim();
  const password = body.password || "";

  const user = await env.DB.prepare(
    "SELECT id, username, password_hash, salt, class_name, role FROM users WHERE username = ?"
  )
    .bind(username)
    .first();
  if (!user) return json({ error: "Incorrect username or password." }, 401);

  const candidate = await hashPassword(password, user.salt);
  if (!timingSafeEqual(candidate, user.password_hash)) {
    return json({ error: "Incorrect username or password." }, 401);
  }

  return startSession(env, user.id, user);
}

async function startSession(env, userId, user) {
  const token = randomHex(32);
  const ttlDays = Number(env.SESSION_TTL_DAYS) || DEFAULT_SESSION_TTL_DAYS;
  const maxAgeSeconds = ttlDays * 24 * 60 * 60;
  await env.DB.prepare("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, datetime('now', ?))")
    .bind(token, userId, "+" + ttlDays + " days")
    .run();

  return json(
    { username: user.username, class_name: user.class_name, role: user.role },
    200,
    { "Set-Cookie": sessionCookieHeader(token, maxAgeSeconds) }
  );
}

async function handleLogout(request, env) {
  const token = parseCookie(request, SESSION_COOKIE);
  if (token) await env.DB.prepare("DELETE FROM sessions WHERE token = ?").bind(token).run();
  return json({ ok: true }, 200, { "Set-Cookie": clearCookieHeader() });
}

async function handleMe(request, env) {
  const user = await getSessionUser(request, env);
  if (!user) return json({ error: "Not logged in." }, 401);
  return json({ username: user.username, class_name: user.class_name, role: user.role });
}

async function handleGetProgress(request, env) {
  const user = await getSessionUser(request, env);
  if (!user) return json({ error: "Not logged in." }, 401);
  const row = await env.DB.prepare("SELECT data, updated_at FROM progress WHERE user_id = ?").bind(user.id).first();
  return json({ data: row ? JSON.parse(row.data) : {}, updated_at: row ? row.updated_at : null });
}

async function handlePutProgress(request, env) {
  const user = await getSessionUser(request, env);
  if (!user) return json({ error: "Not logged in." }, 401);
  const body = await request.json().catch(() => null);
  if (!body || typeof body.data !== "object") return json({ error: "Body must be { data: {...} }." }, 400);

  const serialized = JSON.stringify(body.data);
  if (serialized.length > 200000) return json({ error: "Progress payload too large." }, 413);

  await env.DB.prepare(
    "INSERT INTO progress (user_id, data, updated_at) VALUES (?, ?, datetime('now')) " +
      "ON CONFLICT(user_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at"
  )
    .bind(user.id, serialized)
    .run();

  return json({ ok: true });
}

// Class-level rollup for a future teacher dashboard (Phase 3); harmless to expose now —
// only returns usernames/class for the caller's own class, no passwords.
async function handleClassRoster(request, env) {
  const user = await getSessionUser(request, env);
  if (!user || !user.class_name) return json({ error: "Not logged in or no class assigned." }, 401);
  const rows = await env.DB.prepare(
    "SELECT u.username, p.updated_at FROM users u LEFT JOIN progress p ON p.user_id = u.id WHERE u.class_name = ?"
  )
    .bind(user.class_name)
    .all();
  return json({ class_name: user.class_name, students: rows.results || [] });
}

const ROUTES = [
  ["POST", "/api/signup", handleSignup],
  ["POST", "/api/login", handleLogin],
  ["POST", "/api/logout", handleLogout],
  ["GET", "/api/me", handleMe],
  ["GET", "/api/progress", handleGetProgress],
  ["PUT", "/api/progress", handlePutProgress],
  ["GET", "/api/class/roster", handleClassRoster],
];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = corsHeaders(request, env);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    const route = ROUTES.find(([method, path]) => method === request.method && url.pathname === path);
    if (!route) return json({ error: "Not found." }, 404, cors);

    try {
      const response = await route[2](request, env);
      Object.entries(cors).forEach(([k, v]) => response.headers.set(k, v));
      return response;
    } catch (err) {
      const response = json({ error: "Server error." }, 500);
      Object.entries(cors).forEach(([k, v]) => response.headers.set(k, v));
      return response;
    }
  },
};
