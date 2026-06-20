# Character Studio backend — Cloudflare Worker + D1

Phase 2 backend: real username/password accounts and server-side learning
progress, replacing the client-side passcode gate. Frontend stays a static
site on GitHub Pages; this Worker is the only new moving part.

## What it is

- **Cloudflare Workers** (free tier) — the API (`src/index.js`).
- **Cloudflare D1** (free tier, SQLite) — `users`, `sessions`, `progress` tables
  (`schema.sql`).
- Auth: PBKDF2-hashed passwords, random session tokens stored in `sessions`
  and set as an `HttpOnly; Secure; SameSite=None` cookie — no JWT, no third
  auth provider, real logout (deletes the DB row).
- Progress sync: one JSON blob per student (`progress.data`), the same shape
  the app already kept in `localStorage` (`{ mastery, learn, last }`) — so the
  frontend just GETs it on login and PUTs it after each change.

## One-time setup (you do this — needs your Cloudflare login)

```bash
cd backend
npm install                      # installs wrangler (CLI) locally
npx wrangler login                # opens a browser to authorize the CLI

# 1. Create the D1 database
npx wrangler d1 create studio-db
# ↳ copy the "database_id" it prints into wrangler.toml (REPLACE_WITH_D1_DATABASE_ID)

# 2. Apply the schema
npm run db:migrate

# 3. Set the allowed frontend origin(s) (comma-separated, no trailing slash, no wildcard).
#    This MUST be the exact origin the site is served from, e.g.:
#    https://chaussen.github.io   or   https://studio.caseychinese.org
npx wrangler secret put ALLOWED_ORIGIN

# 4. Deploy
npm run deploy
```

Wrangler will print the Worker's URL, e.g. `https://studio-api.<your-subdomain>.workers.dev`.

## Point the frontend at it

In `studio.html`, set the API base before `learn/app.js` loads:

```html
<script>window.STUDIO_API_BASE = "https://studio-api.<your-subdomain>.workers.dev";</script>
```

(Already wired up — see `studio.html`. Just replace the placeholder URL with
your real Worker URL after deploying.)

## Custom domain (recommended once you're happy it works)

Cross-site cookies (`SameSite=None`) work fine on `workers.dev`/`github.io`,
but for the cleanest setup put both on the same apex domain, e.g.:

- Frontend: `studio.caseychinese.org` (already documented in `ROADMAP.md`)
- API: `api.caseychinese.org` → Workers → Routes → add a custom domain in the
  Cloudflare dashboard (Workers & Pages → studio-api → Settings → Domains & Routes)

Then `ALLOWED_ORIGIN` becomes `https://studio.caseychinese.org` and cookies
can use `SameSite=Lax` (edit `sessionCookieHeader`/`clearCookieHeader` in
`src/index.js` if you make this switch).

## Local development

```bash
npm run db:migrate:local   # seeds a local SQLite copy under .wrangler/
npm run dev                # runs the Worker on http://localhost:8787
```

Point `window.STUDIO_API_BASE` at `http://localhost:8787` while testing.

## Data collected

Per the duty-of-care note in `ROADMAP.md`: just a username (not a real name),
a password (hashed, never stored in plain text), an optional class name, and
the existing progress data (which characters are mastered + UI prefs). No
other personal data is collected.

## Future (Phase 3 — teacher dashboard)

`GET /api/class/roster` already returns the student list + last-updated
timestamp for the caller's class — enough to build a "who's done what" teacher
view without further schema changes.
