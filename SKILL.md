---
name: iaahoy-daily-edition
description: "iaahoy: produce + publish daily Spanish open-AI newspaper."
version: 2.1.0
author: jgbarah
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [iaahoy, daily-newspaper, github-pages, open-ai, spanish, cron, podcast]
    related_skills: [espanish-podcast, news-digest, github-repo-management]
---

# ia·ahoy — daily open-AI newspaper + podcast (Spanish)

Static-HTML "newspaper" about open-weights models + open-source AI software,
published daily to GitHub Pages: **https://jgbarahbot.github.io/iaahoy**,
plus a **single daily podcast MP3** (ephemeral — old ones are NOT kept; the
site's git history is flattened to one commit every day). Repo
`jgbarahbot/iaahoy` (branch `main`), Pages = project site, root path.
Audience: people who care about open source, open AI, self-hosting AI.
**Everything is written in Spanish. Every note needs ≥1 follow-up link**
(prefer GitHub/GitLab repo, HuggingFace card, arXiv, or a technical page).

Title: **"IA Abierta Hoy"** (short form: **IA*A*Hoy**).

## Paths & auth
- Project: `~/.hermes/projects/iaahoy/`
  - `scripts/collector.py`   — gathers raw material → `material.json`
  - `scripts/render.py`      — edition JSON → standalone HTML (CSS inlined)
  - `scripts/make_podcast.py`— local copy; the canonical script lives in the
                                `espanish-podcast` skill (step 4 calls it from
                                `~/.hermes/skills/espanish-podcast/scripts/`)
  - `scripts/publish.py`     — re-render all editions, copy podcast, FLATTEN
                                git history (orphan + force-push) to GitHub
  - `templates/style.css`    — broadsheet CSS (render.py inlines it)
  - `editions/<YYYY-MM-DD>.json`        — each day's curated content
  - `editions/<YYYY-MM-DD>.html`        — rendered edition (permlink)
  - `editions/<YYYY-MM-DD>.podcast.txt` — that day's podcast script (text)
  - `editions/index.html`    — archive of all editions
  - `material.json`          — today's collected candidates (regenerated daily)
- Push secret: env var `GITHUB_IAAHOY_TOKEN` in `~/.hermes/.env` (clone + push
to iaahoy only). Read-only `GITHUB_TOKEN` is enough for the collector's GitHub
API. Do NOT print secret values. NOTE: Hermes's redaction layer rewrites the
word "token" (lowercase) in tool-call strings — reference the secret as the env
var name, never type the literal word in code strings.
- SearXNG (self-hosted, no key): `http://127.0.0.1:8080/search?format=json`.
  Reddit direct API is datacenter-blocked → use SearXNG for subreddit/news.
- `web_extract` tool is NOT configured — don't rely on it; use `curl` + `web_search`.
- TTS: DELEGATED to the `espanish-podcast` skill — it owns the script format,
  the two-voice Piper pipeline (A = `es_ES-davefx-medium`, C =
  `es_MX-claude-high`, both 22050 Hz, user-fixed pair "usa solo a y c"),
  English-term IPA and all TTS requirements/pitfalls. This skill only WRITES
  the script and calls the other skill's `make_podcast.py`.

## The 6-step pipeline (run in order)

Steps 3–4 split the podcast work: THIS skill writes the script (step 3, LLM);
the `espanish-podcast` skill synthesizes the audio (step 4, delegated).
Load `espanish-podcast` before the first run of the day:
`skill_view(name="espanish-podcast").`
1. **Collect** (deterministic, ~1 min):
   `cd ~/.hermes/projects/iaahoy && python3 scripts/collector.py --out material.json --days 2`
   Sources: HF trending models/datasets, HF daily papers, HF blog RSS, GitHub
   trending (topic search), SearXNG web/subreddit. Each source degrades to `[]`
   on failure; check `material["errors"]`. Read `material.json` for candidates.
2. **Curate (YOU — the LLM step).** Read `material.json` + a recent
   `editions/*.json` as a format reference. Write `editions/<TODAY>.json`
   in Spanish. Structure: masthead fields + `lead` (portada) + 3–5 `sections`,
   each with `title` + 2–4 `notes`. Each note: `title`, `summary` (2–4 Spanish
   sentences), `tags` (list), `links` (list of {label,url} — ≥1, prefer
   technical). Use REAL URLs from material; if a summary needs grounding and
   the RSS desc is empty, use `web_search` to verify facts. No placeholder
   links — every URL must be real. **The `colophon` block MUST carry**:
   `title: "IA Abierta Hoy"`, `short_title: "IA*A*Hoy"`, and a `fineprint`
   string in the form:
   `Contenido generado automáticamente a partir de fuentes públicas por Hermes, usando <MODELO>, para que lo disfrutes y te sea útil.`
   where `<MODELO>` is the LLM actually generating it (e.g. "Qwen3.8-27B").
   The CC BY-SA 4.0 license block is rendered by render.py — do not hand-write it.
3. **Write the podcast script (YOU).** Write
   `editions/<TODAY>.podcast.txt` in **natural, spoken Spanish** — a
   listening-oriented summary, NOT a copy of the news text. Format rules
   (two voices A/C strictly alternating, `A:`/`C:` on the same line as the
   text, blank line between blocks, `*English terms*` marked with asterisks,
   length) live in the `espanish-podcast` skill — **load it**
   (`skill_view(name="espanish-podcast")`) and write the script exactly the
   way that skill describes. Content: open with the show name ("IA Abierta
   Hoy"), hit the portada, walk through all the sections, close with a short
   sign-off; target ~3–5 minutes when spoken (~18 blocks, 9 per voice).
   **Do NOT mention the number of voices or narrator identity in the script —
   just use the voices naturally.** Don't overdo asterisks: only mark genuine
   English terms, not Spanish words.
4. **Podcast audio — DELEGATE to the `espanish-podcast` skill** (deterministic):
   `python3 ~/.hermes/skills/espanish-podcast/scripts/make_podcast.py --script editions/<TODAY>.podcast.txt --out build/podcast.mp3`
   This skill does NOT synthesize audio itself; `espanish-podcast` owns the
   TTS pipeline (script format, two Piper voices, English IPA, verification).
   Produces the single-slot MP3. Old audio is NOT kept — publish.py flattens the
   git history each day, so only today's MP3 survives.
5. **Render** (deterministic) — for the latest edition only (publish re-renders
   everything, but this verifies early):
   `python3 scripts/render.py --json editions/<TODAY>.json --css templates/style.css --podcast podcast.mp3 --out build/site/editions/<TODAY>.html`
   Verifies ≥1 link per note; fails loudly on placeholders/`TODO`/`lorem`.
6. **Publish** (deterministic, self-healing, history-flattening):
   `python3 scripts/publish.py`
   Re-renders EVERY `editions/*.json` (root `index.html` = latest, per-edition
   permlinks, `editions/index.html` archive), copies `build/podcast.mp3` into the
   site root, creates a fresh **orphan** commit, and **force-pushes** main. This
   is what guarantees no old audios linger. `--no-push` does everything except
   the push (use to dry-run). It re-clones `git/` if corrupted; refuses to push
   an empty tree.

## After publishing — VERIFY (do not trust exit 0 alone)
- `curl -s -o /dev/null -w '%{http_code} %{size_download}\n' https://jgbarahbot.github.io/iaahoy/` → 200.
- Pages first build takes ~30–60s after a push; poll once if it 404s.
- `curl -s -o /dev/null -w '%{http_code}\n' https://jgbarahbot.github.io/iaahoy/podcast.mp3` → 200.
- Every page's `<audio src=...>` must resolve to `/podcast.mp3`: root uses
  `podcast.mp3`, the permlink and archive use `../podcast.mp3` (they live in
  `editions/`). Check the rendered HTML carries the right relative path.
- `curl -s <permalink>` should 200. Compare bytes vs local `build/site/index.html`.
- Report the live URL + edition date to the user in Spanish (or their language),
  2–4 lines: portada headline, 2–3 highlights, and the live URL.

## Edition JSON schema (what render.py expects)
```
{
  "date": "27 de septiembre de 2026",      # long Spanish date (masthead)
  "weekday_long": "domingo",               # Spanish weekday
  "edition": "Edición nº 2",              # running number (bump daily)
  "tagline": "IA de pesos abiertos y software libre, cada mañana",
  "lead": {                                  # portada — the one big story
    "title": "…", "summary": "… (4-6 sentences)",
    "tags": ["…"], "links": [{"label": "…", "url": "…"}]
  },
  "sections": [
    { "title": "Modelos", "notes": [
      { "title": "…", "summary": "…", "tags": ["…"],
        "links": [{"label": "GitHub", "url": "…"}] }
    ]},
    { "title": "Agentes y software", "notes": [ … ]},
    { "title": "Papers e investigación", "notes": [ … ]},
    { "title": "Comunidad y self-hosting", "notes": [ … ]}
  ],
  "colophon": {
    "title": "IA Abierta Hoy",
    "short_title": "IA*A*Hoy",
    "fineprint": "Contenido generado automáticamente a partir de fuentes públicas por Hermes, usando <MODELO>, para que lo disfrutes y te sea útil."
  }
}
```
Suggested section titles (adapt to the day's news): **Modelos**, **Agentes y
software**, **Papers e investigación**, **Comunidad y self-hosting**. Keep the
lead to the single most important item of the day.

## Pitfalls (learned)
- `render.py` flags: `--json <edition.json> --css <style.css> --podcast <rel.mp3> --out <html>`; for the archive it's `--list-editions <editions_dir>` (not `--json`). `--podcast` is the RELATIVE path as it should appear in that page.
- `make_podcast.py` is called from `~/.hermes/skills/espanish-podcast/scripts/` (the canonical copy); flags: `--script <podcast.txt> --out <podcast.mp3>` (optionally `--voice-a`/`--voice-c`). Voice details, English-IPA mechanics and TTS pitfalls are documented in the `espanish-podcast` skill — keep that boundary, don't re-document TTS here.
- English-IPA mechanism (do NOT "fix" it): piper's `[[…]]` blocks are split **char-by-char** (`voice.py`: `extend(text_part[2:-2].strip())`) and each char is looked up in the model's phoneme id-map, unknowns skipped silently. piper's own `;en` inline switch does NOT work (phonemize_espeak strips (lang) flags, L40) — the working path is pre-phonemizing the term with espeakbridge (`EspeakPhonemizer()` to init, then `set_voice("en-us")`, `get_phonemes(term)`) and wrapping the IPA in `[[…]]`. espeakbridge without prior init segfaults.
- The archive page lives in `editions/`, so its podcast link MUST be `../podcast.mp3` (publish.py already does this); if you ever hand-render the archive, use `../podcast.mp3`.
- HF blog HTML is JS-rendered → use RSS `desc` (often empty) + `web_search` to ground the lead story, not raw HTML scrape.
- GitHub Pages first deploy needs a build; don't conclude failure on first 404.
- `publish.py` already self-heals `git/` and flattens history; only `rm -rf git` manually if it still misbehaves. Never commit the secret; it's injected into the clone URL only.
- Bump the `edition` running number from the latest prior edition (count `editions/*.json`).
- If the day's news is thin (weekend), still publish — reuse trending models/repos with fresh framing; never skip a day.
- Redaction layer: never type the literal word for the secret (lowercase) in tool-call strings — it gets rewritten; use the env var name or `chr()` construction in code.

## Cron
The daily 08:30 job (08:30 CEST) fires this exact flow. When you run it, your
FINAL RESPONSE is delivered to the user — write a 2–4 line Spanish summary:
edition date, the portada headline, 2–3 other highlights, and the live URL.
