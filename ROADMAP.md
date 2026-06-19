# Casey Chinese — Public Site & Studio Roadmap

Planning/handoff notes for future sessions, focused on **taking the tools public**
and the follow-ups deferred along the way. For Character Studio's internal
engineering/content model see `Character Studio - HANDOFF.md`. Updated 2026-06-16.

---

## Where things stand (Phase 1 — DONE)

The whole thing is a **static site published to GitHub Pages via GitHub Actions**
(`.github/workflows/deploy-pages.yml`), assembled into one artifact:

| URL path | Content | Source |
|---|---|---|
| `/`          | Landing / hub (advertising face) | `landing/index.html` |
| `/studio/`   | Character Studio learning app    | `studio.html` + `learn/` + `audio/` |
| `/cardmaker/`| Card Maker web app               | built from `cardmaker/` (`npm run web:build`) |

- **Pages Source must be "GitHub Actions"** (Settings → Pages). The legacy Jekyll
  "deploy from a branch" build serves the generic welcome page and must stay OFF.
- Studio access is a **client-side passcode (`2580`)** — a *soft gate only*. The
  code is in `learn/app.js`, readable by anyone. Fine for now; not real security.
- Progress is stored **per-browser in localStorage** (anonymous, no PII, no server).

---

## Operational: custom domain (ready to switch on)

The school owns **caseychinese.org** and wants the Studio on a subdomain.

1. DNS at the registrar: add `studio  CNAME  chaussen.github.io.`
2. Re-enable the CNAME line in `deploy-pages.yml` (currently commented out:
   `echo "studio.caseychinese.org" > "$SITE/CNAME"`), push.
3. Settings → Pages → set Custom domain `studio.caseychinese.org`, then tick
   **Enforce HTTPS** once the cert provisions.

Note: the CNAME was intentionally left off so the `chaussen.github.io/...` URL
stays testable. With it on, the github.io URL 301-redirects to the subdomain, so
only enable once DNS resolves.

---

## Phase 2 — real accounts + saved progress (the main next build)

Goal decided with the school: **one codebase, two access tiers** — a public
**taster** (open, for advertising/SEO; e.g. one book/lesson unlocked) and the
full app behind a **real login**. Students use it at school *and* home, ~4–5
classes × up to 15 (Prep–Y8), growing.

- **Keep the frontend static on Pages.** Add a free backend — **Supabase**
  (Postgres + Auth + row-level security; free tier far exceeds this scale) or
  Firebase — for:
  - real authentication (username + password, or class-code + name) that replaces
    the client-side passcode as the *actual* gate;
  - **per-student progress/results saved server-side** (so home practice counts
    and is visible to teachers).
- **Don't** move lesson data behind the API just to "protect" it — the content
  isn't secret IP, and all of `learn/*.js` is downloadable from a static host
  regardless. An account gate is enough to keep outsiders out of the guided
  experience.
- **Children's data duty of care:** collect the minimum (a username — avoid full
  real names if possible — class, progress), pick an appropriate data region
  (EU/AU), and get parent consent at signup. Today the app stores nothing
  personal; preserve that discipline.
- Why not Cloudflare Access (the other free real-gate): free tier caps at 50
  seats and gives no progress tracking — already too small and the wrong tool.

## Phase 3 — teacher dashboard

Once Phase 2 stores results: a teacher view of completion + scores per class,
weak characters per student/class. Grows naturally from the Phase 2 schema.

---

## Tech debt / smaller follow-ups (discovered during Phase 1)

- **Stroke animation is gated by `prefers-reduced-motion`.** This is *why* the
  player shows no animation in Edge/Firefox when the OS has "reduce motion" on
  (Chrome on the same machine wasn't reporting it). The stroke-order build is
  **functional teaching content, not decoration**, so consider: always animate on
  an explicit Replay/Step press (and/or offer an in-app toggle), and only skip
  *auto*-play under reduced motion. See `tweenDash`/`makeWriter` in `learn/app.js`.
- **`learn/explorer.js` still uses `element.animate()` for stroke-dashoffset** —
  the same WAAPI/Firefox gap fixed in `app.js` via `tweenDash`. If the standalone
  character-explorer page is still used, port it to `tweenDash` too.
- **Recogniser, further hardening:** position tolerance now scales with stroke
  length (fixes dense characters like 雨). A stronger version would make the box
  *neighbour-aware* — tolerance ≈ half the distance to the nearest other stroke's
  endpoints — so adjacent strokes can never be confused even in the free-sketch
  grader. (`strokeMatch` in `learn/app.js`.)
- **Asset cache-busting:** only the three changed engine scripts carry `?v=` in
  the HTML; the big data files don't. When data files change, bump a shared
  version (or hash filenames in the build) so browsers refetch.
- **Content authoring gaps** (see HANDOFF §5/§10): origin stories + sentences are
  the biggest gap; finish 中文 Book 1 (45 chars still missing stroke data, §6).

---

## Quick reference

- Deploy: push to `master` touching `landing/`, `studio.html`, `learn/`,
  `audio/`, `cardmaker/`, or the workflow → Actions builds + deploys.
- Local studio test: serve the repo root and open `studio.html`
  (everything is relative-pathed).
- Bump `studio.css?v=YYYYMMDD` (and the `?v=` on changed scripts) after edits —
  browsers cache hard.
