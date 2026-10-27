---
name: iaahoy-daily-edition
description: "iaahoy: produce + publish daily Spanish open-AI newspaper."
version: 2.24.0
author: jgbarah
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [iaahoy, daily-newspaper, github-pages, open-ai, spanish, cron, podcast, illustration]
    requires_skills: [espanish-podcast, moss-image-news-illustration]
    related_skills: [news-digest, github-repo-management, hyperqwen-gpu-swap, espanish-podcast, moss-image-news-illustration]
---

# ia·ahoy — daily open-AI newspaper + podcast + cover illustration (Spanish)

**Every edition carries a photorealistic cover illustration** (step 3),
generated with MOSS-Image on the GPU and placed between the lead's
summary (entradilla) and its first body paragraph. The **illustration
pipeline is owned by the `moss-image-news-illustration` skill** — this
skill only drives it as part of the daily flow: read the lead, design and
fidelity-review the scene prompt, write the batch JSON, launch the MOSS
GPU swap, and (when the LLM is back) integrate the chosen image into the
edition JSON as `lead.illustration`.

**Podcast synthesis runs on the GPU** (step 5) via the `hyperqwen-gpu-swap`
skill: a detached systemd user job stops the HyperQwen vLLM container,
synthesizes the script on the RTX 3090 and restarts vLLM. The **voice
engine is owned by the `espanish-podcast` skill** — this skill only writes
the script and launches the swap. The current default engine is Qwen3-TTS
1.7B-Base voice-clone (two cloned narrators, no per-block emotion); the
alternative engines (CosyVoice3 with emotion instruct, Qwen3-TTS
VoiceDesign synthetic) are selectable via `--engine` in
`make_podcast.py` — see the espanish-podcast skill for details.
Install the podcast skill first (it owns all voice generation):
`hermes skills install github.com/jgbarahbot/espanish-podcast`.
Install the illustration skill first as well:
`hermes skills install github.com/jgbarahbot/moss-image-news-illustration`.

Static-HTML "newspaper" about open-weights models + open-source AI software,
published daily to GitHub Pages: **https://jgbarahbot.github.io/iaahoy**,
plus a **single daily podcast MP3** (ephemeral — old ones are NOT kept; the
site's git history is flattened to one commit every day). Repo
`jgbarahbot/iaahoy` (branch `main`), Pages = project site, root path.
Audience: people who care about open source, open AI, self-hosting AI.
**Everything is written in Spanish. Every note needs ≥1 follow-up link**
(prefer GitHub/GitLab repo, HuggingFace card, arXiv, or a technical page).

Title: **"IA·A·Hoy"** (middle dots, as in the masthead; short form **IA*A*Hoy**). Both the HTML `<title>` and the visible H1 use `IA·A·Hoy` (render.py v2.21 handles it).

## Paths & auth
- Project: `~/.hermes/projects/iaahoy/`
  - `scripts/collector.py`   — gathers raw material → `material.json`
  - `scripts/render.py`      — edition JSON → standalone HTML (CSS inlined).
                                v2.19: `esc_em()` turns *term* markers in
                                title/summary/body into <em>term</em> (the
                                two-pass English-term convention); a lone `*`
                                passes through untouched. v2.23: renders
                                `lead.illustration` as a <figure> between the
                                summary and the first body paragraph (the
                                cover illustration, step 3).
  - (podcast audio is synthesized in step 4 — DELEGATED to the
                                `espanish-podcast` skill: it owns the engine,
                                the GPU worker and the CPU fallback. This
                                skill never re-documents voice internals here.)
  - `scripts/publish.py`     — re-render all editions, copy podcast, FLATTEN
                                git history (orphan + force-push) to GitHub
  - `templates/style.css`    — broadsheet CSS (render.py inlines it).
                                **Responsive convention (user rule
                                2026-10-25):** the site must work at every
                                screen size with NO horizontal scroll. Keep
                                it that way when editing the CSS:
                                long unbreakable tokens (repo slugs like
                                `owner/Repo-Quantized`, URLs) must wrap —
                                `body` carries `overflow-wrap:anywhere` and
                                `.chip` is `white-space:normal` +
                                `max-width:100%` (NEVER `white-space:nowrap`
                                on chips — a 35-char slug once forced the
                                whole portada to 487 px at a 360 px
                                viewport). Children of grid/flex that hold
                                long text carry `min-width:0` (`.wrap`,
                                `.note`, `.chips`). Fluid layout is
                                `clamp()` + single column below 860px (fbody
                                2→1 at 640px); the `@media(max-width:480px)`
                                block trims phone-sized fixed values (h1,
                                padding, drop cap). Verify any CSS change in
                                a real browser sweep (320–1280 px) before
                                publishing.
  - `editions/<YYYY-MM-DD>.json`        — each day's curated content
  - `editions/<YYYY-MM-DD>.html`        — rendered edition (permlink)
  - `editions/<YYYY-MM-DD>.podcast.txt` — that day's podcast script (text)
  - `editions/index.html`    — archive of all editions
  - `material.json`          — today's collected candidates (regenerated daily)
  - `build/assets/lead-illo-<YYYY-MM-DD>.jpg` — the day's cover illustration
                                (PNG → JPEG, step 3); publish.py copies it to
                                the site root as `assets/`
- Push secret: env var `GITHUB_IAAHOY_TOKEN` in `~/.hermes/.env` (clone + push
to iaahoy only). Read-only `GITHUB_TOKEN` is enough for the collector's GitHub
API. Do NOT print secret values. NOTE: Hermes's redaction layer rewrites the
word "token" (lowercase) in tool-call strings — reference the secret as the env
var name, never type the literal word in code strings.
- **Parameterized GitHub identity (no hardcoded username/repo/token in code):**
  `publish.py` and `sync.sh` resolve everything as CLI > env > derived:
  - GitHub username → `--user` / `IAAHOY_GH_USER` / **token's own login**
    (derived via `GET https://api.github.com/user` with the token).
  - push token var → `--token-env` (default `GITHUB_IAAHOY_TOKEN`).
  - site repo URL → `--repo` / `IAAHOY_SITE_REPO` (default `https://github.com/<user>/iaahoy.git`).
  - Pages URL → `--site-url` / `IAAHOY_SITE_URL` (default derived from repo).
  To retarget another account, set `IAAHOY_GH_USER` and `IAAHOY_SITE_REPO` in
  `~/.hermes/.env` — no code edit. Same rule for `sync.sh`: `SKILL_REPO=<owner>/<name>`
  (default `<owner>/<skill-name>`) + `SKILL_TOKEN_ENV` (default `GITHUB_CONTENT_RW_TOKEN`);
  the token's login is used as the git auth user automatically.
- SearXNG (self-hosted, no key): `http://127.0.0.1:8080/search?format=json`.
  Reddit direct API is datacenter-blocked → use SearXNG for subreddit/news.
- `web_extract` tool is NOT configured — don't rely on it; use `curl` + `web_search`.
- TTS: DELEGATED to the `espanish-podcast` skill — it owns the script
  format, the voice engine and all TTS requirements/pitfalls. Current
  default: **Qwen3-TTS 1.7B-Base voice-clone** (two cloned narrators A/C,
  no per-block emotion, 24 kHz); the other engines (CosyVoice3 with
  emotion instruct, Qwen3-TTS VoiceDesign synthetic) and the Piper fallback
  are selectable in `make_podcast.py` via `--engine` / `--mode`. This skill
  only WRITES the script; synthesis runs in step 5 (GPU by default, the
  `espanish-podcast` skill's `make_podcast.py` as CPU fallback). After a
  podcast run, relay any `UNSURE: <term>` lines the script prints to the
  user (they are pronunciation candidates for `pron_dict.json`).

## The 6-step pipeline (run in order)

Steps 4–5 split the podcast work: THIS skill writes the script (step 4, LLM);
step 5 synthesizes it via the `hyperqwen-gpu-swap` skill (GPU) using the
`espanish-podcast` skill's engine (default: Qwen3-TTS voice-clone; `--engine`
selects alternatives — see that skill). Step 3 (cover illustration) is a
separate MOSS-Image GPU swap owned by the `moss-image-news-illustration`
skill. Load `hyperqwen-gpu-swap`, `espanish-podcast` and
`moss-image-news-illustration` before the first run of the day.

**Two GPU swaps, two LLM-off windows:** the MOSS swap (step 3) and the
podcast swap (step 5) both stop vLLM, so the agent loses its own LLM in
each — end your turn right after launching each one (same hard rule as the
podcast swap below). The order is fixed: illustration swap (step 3, end
turn) → when alive again, integrate the image into the JSON → write the
podcast script (step 4) → podcast swap (step 5, end turn) → verify (step
6). `lead.illustration` MUST be in the JSON before the podcast swap,
because that swap's publish renders from the JSON.
0. **PRE-FLIGHT: vLLM health (obligatorio, antes de todo).** Todo el
   pipeline (pasos 1-3) corre sobre el vLLM de HyperQwen
   (127.0.0.1:8081). Si esta caido o en zombi (contenedor `Up` pero
   `/v1/models` no responde — incidente 2026-10-19: zombi de 06:43 a
   08:40; el cron de 08:30 fallo en silencio y se perdio la edicion del
   dia), el cron entero fallara sin producir nada. Comprobar:
   `curl -s -m 5 http://127.0.0.1:8081/v1/models | grep qwen3.8-27b`.
   Si no responde: `bash /home/jgb/hyperqwen/hyperqwen_on.sh` — es
   idempotente (no toca nada si ya sirve), en zombi fuerza
   stop+start, espera un chat/completions real, y esta serializado con
   flock (dos recuperaciones no compiten; si no toma el lock a tiempo,
   cede al otro). Esperar a que termine (hasta ~20 min), re-comprobar y
   solo entonces continuar con el pipeline.
1. **Collect** (deterministic, ~1 min):
   `cd ~/.hermes/projects/iaahoy && python3 scripts/collector.py --out material.json --days 2`
   Sources: HF trending models/datasets, HF daily papers, HF blog RSS, GitHub
   trending (topic search), SearXNG web/subreddit. Each source degrades to `[]`
   on failure; check `material["errors"]`. Read `material.json` for candidates.
2. **Curate (YOU — the LLM step).** Read `material.json` + a recent
   `editions/*.json` as a format reference. Write `editions/<TODAY>.json`
   in Spanish. Structure: masthead fields + `lead` (portada) + 3–5 `sections`,
   each with `title` + 2–4 `notes`. **Standard sections (user convention
   2026-10-25, adapt to the day's news):** **Modelos**, **Agentes libres**,
   **Software libre para IA**, **Papers e investigación**, **Comunidad y
   self-hosting**. The agent/software split: **Agentes libres** = free
   *agents* (new agents, improvements to existing ones, skills for agents,
   novel uses of agents); **Software libre para IA** = non-agent open-source
   AI software (engines, CLIs, monitors, runtimes, tools). Both carry a
   similar number of notes as the other sections. **Lead length:** the
   portada may run to **700–800 words** when the story has real material
   (do not pad it when it doesn't); regular notes stay ~120–250 words. Each
   note follows the **two-pass Spanish method** (see below): `title`,
   `summary` (ONE recap paragraph), `body`
   (list of flowing paragraphs — the actual article), `tags` (list), `links`
   (list of {label,url} — ≥1, prefer technical). Use REAL URLs from material;
   if a summary needs grounding and the RSS desc is empty, use `web_search`
   to verify facts. No placeholder links — every URL must be real. **The
   `colophon` block MUST carry**:
   `title: "IA Abierta Hoy"`, `short_title: "IA*A*Hoy"`, and a `fineprint`
   string in the form:
   `Contenido generado automáticamente a partir de fuentes públicas por Hermes, usando <MODELO>, para que lo disfrutes y te sea útil.`
   where `<MODELO>` is the LLM actually generating it (e.g. "Qwen3.8-27B").
   It MUST also carry the `made_with` list (the THREE skill names with their
   GitHub repo URLs, see the schema) — it renders the "Hecho con Hermes" note.
   The CC BY-SA 4.0 license block is rendered by render.py — do not hand-write it.
3. **Cover illustration (MOSS-Image) — GPU swap, then integrate when alive.**
   The recipe — prompt formula, negative prompt, fidelity review, batch and
   swap scripts, pre-flight — lives in the `moss-image-news-illustration`
   skill; this step only drives it for the day's lead:
   1. Read the FULL lead (`lead.body` of the JSON you just wrote) and design
      ONE concrete scene around the story's central concept (per that skill:
      concrete objects, positions, sizes, light, mood; 60–120 words; no
      vague "suggesting …"; no numbers or actions the article does not
      make). Run its **fidelity review** against the article before
      generating.
   2. Write the batch JSON to `~/.hermes/gpu-swaps/iaahoy<NN>_r1.json`
      (4 seeds is the daily default — one swap, ~8–17 min total).
   3. Pre-flight per that skill: `json.load` the batch; `/tmp/gpu-swap.lock`
      free; vLLM serving; `bash -n` target + swap scripts.
   4. Launch the MOSS swap as a DETACHED systemd job (the moss skill's
      target/swap scripts, env-driven LOG/PROMPTS; per-round unit name,
      e.g. `gpu-swap-iaahoy<NN>-r1`; `TimeoutStartSec=0`,
      `KillMode=process`). **End your turn right after launching** — the
      OFF phase takes vLLM down with you.
   5. When alive again: the swap log must say `SWAP COMPLETO: target rc=0,
      on rc=0` and vLLM must serve again; count the PNGs in
      `~/.hermes/gpu-swaps/moss-out/`. The local LLM has **no vision**
      (`vision_analyze` returns 400 on these) — the user judges the
      images; if they do not pick a specific one, use the **first
      seed's** output. Convert the chosen PNG to JPEG (PIL, quality 88)
      as `~/.hermes/projects/iaahoy/build/assets/lead-illo-<TODAY>.jpg`
      and add to the edition JSON:
      `lead.illustration = {"file": "lead-illo-<TODAY>.jpg", "alt": "<scene, in Spanish>", "caption": "Ilustración de la portada, generada con MOSS-Image: <one line>"}`.
      render.py (v2.23.0) then places the figure between the summary and
      the first body paragraph automatically; publish.py copies
      `build/assets/*` to the site root (`assets/<file>` from index.html,
      `../assets/<file>` from the permalinks).
   **Fallback:** if the MOSS swap fails twice, publish WITHOUT the
   illustration (omit the field — render.py skips the figure) and tell the
   user; never block the daily edition on the illustration.
4. **Write the podcast script (YOU).** Write
   `editions/<TODAY>.podcast.txt` in **natural, spoken Spanish** — a
   listening-oriented summary, NOT a copy of the news text. Format rules
   (two voices A/C strictly alternating, `A:`/`C:` on the same line as the
   text, blank line between blocks, `*English terms*` marked with asterisks,
   length) live in the `espanish-podcast` skill — **load it**
   (`skill_view(name="espanish-podcast")`) and write the script exactly the
   the way that skill describes. **Source of the script (user rule
   2026-10-25): derive it from the day's edition text itself** — the JSON
   you just wrote (already passed through the two-pass method, i.e. already
   translated) — not from the raw English material: read the portada
   summary + each section's summaries (and skim the bodies) and turn them
   into spoken blocks. Open with the show name ("IA Abierta Hoy"), hit the
   portada, walk through all the sections, close with a short sign-off;
   target ~3–5 minutes when spoken (~18 blocks, 9 per voice). **Translation
   discipline:** the same bar as pasa 1 applies — a term that has an obvious
   Spanish equivalent (*open weights*→pesos abiertos, *coding*→código,
   *trending*→tendencia, *likes*→me gusta) must be in Spanish in the script
   too; asterisks go ONLY on the terms that genuinely stay in English (names,
   acronyms, tools) — and ideally exactly the ones the edition asterisks, so
   the audio and the page stay consistent.
   **Do NOT mention the number of voices or narrator identity in the script —
   just use the voices naturally.** Don't overdo asterisks: only mark genuine
   English terms, not Spanish words. Emotion markers are OPTIONAL: the default
   engine (Qwen3-TTS clone) ignores them, and the `qwen-syn` engine reads the
   Spanish tags (`[alegre]`, `[serio]`, `[cierre]` …) directly — so a marker
   costs nothing in either case; add one only for a deliberate tonal beat
   (opening/closing or a single dramatic note), keep most blocks plain
   `A:`/`C:`. For CosyVoice (`--engine cosy`) the espanish-podcast skill's
   emotion section defines the accepted tags/instructions.
5. **Podcast audio — GPU swap, then render + publish inside the same swap.**
   The **voice engine is owned by the `espanish-podcast` skill** — this step
   only launches the swap; do NOT re-document how the voice is generated
   here (engine internals, emotion, pronunciation and TTS pitfalls all live
   in that skill). The **default engine is Qwen3-TTS 1.7B-Base voice-clone**
   (two cloned narrators A/C, no per-block emotion); the other engines
   (CosyVoice3 with emotion instruct, Qwen3-TTS VoiceDesign synthetic)
   are selectable in `make_podcast.py` via `--engine` / `--mode` if a
   specific episode needs them — see the espanish-podcast skill.
   The swap is a **detached `systemd-run --user` job** that stops vLLM,
   synthesizes the MP3 on the RTX 3090, re-renders + PUBLISHES the site,
   and restarts vLLM (~3–4 min, ~35× faster than CPU). Launch it EXACTLY:
   `systemd-run --user --unit=gpu-swap-iaahoy-podcast --property=TimeoutStartSec=0 --property=KillMode=process bash ~/.hermes/gpu-swaps/qwen3-podcast-gpu-swap.sh /home/jgb/.hermes/projects/iaahoy/editions/<TODAY>.podcast.txt /home/jgb/.hermes/projects/iaahoy/build/podcast.mp3`
   (add `--no-publish` as a 4th arg for a trial that must not touch the
   site/git — the target then only synthesizes the MP3).
   **REGLA DURO — SOLO via systemd-run (incidente 2026-10-19 01:21:
   vLLM caido ~7 h, edicion perdida):** NUNCA lanzar el wrapper como
   hijo de una llamada `terminal`/`execute_code` del agente: esas
   llamadas tienen un timeout duro que, al llegar, manda SIGKILL al
   arbol de procesos — SIGKILL no se puede atrapar, asi que el
   `trap cleanup` del wrapper (el que haria el ON) NUNCA corrio y el
   modelo no volvio hasta que el usuario dio el reboot. `systemd-run
   --user` desacopla el job del arbol de procesos y grupo de procesos
   del agente: sobrevive a la muerte del agente (que durante el OFF
   pierde su LLM de todos modos).
   **What it does** (the `hyperqwen-gpu-swap` skill documents the swap
   mechanism in general): **OFF** stops the HyperQwen vLLM container
   (frees the ~22.5 GB VRAM on the single RTX 3090) → **TARGET**
   `qwen3-podcast-gpu-target.sh` starts the `qwen3-tts:local` container,
   copies in the espanish-podcast worker + `qwen3_podcast.py` + the day's
   script, synthesizes every block and assembles the MP3, then — still
   inside the target, because the agent is dead during the OFF — runs
   `publish.py` (re-render every edition, copy the MP3 to the site root,
   force-push the flattened history) → **ON** restarts vLLM and waits until
   `/health` answers. The target is mode-aware (`--mode clone|design`): it
   mounts the Base model + refs for clone (default) or the VoiceDesign
   model (no refs) for `design`.
   **You MUST end your turn right after launching the swap**: you lose
   your LLM in the OFF phase; the systemd job is detached (the agent can
   die, the chain finishes and vLLM comes back). When you're alive again
   (a later user message or your scheduled turn), verify in **step 5**.
   **Fallback (no GPU available / swap fails twice):** the CPU path via the
   `espanish-podcast` skill's `make_podcast.py` (~25–35 min; then run
   `scripts/render.py` and `scripts/publish.py` from the project dir
   manually). Only if that also OOMs, `--engine piper`.
6. **VERIFY the published site** (run after the swap completes, i.e. in a
   later turn when vLLM is back — do not trust the swap's exit code alone).
   The swap already did render+publish inside the target, so this is
   check-only:
   - `curl -s -o /dev/null -w '%{http_code} %{size_download}\n' https://jgbarahbot.github.io/iaahoy/` → 200.
   - Pages first build takes ~30–60 s after a push; poll once if it 404s.
   - `curl -s -o /dev/null -w '%{http_code}\n' https://jgbarahbot.github.io/iaahoy/podcast.mp3` → 200
     (the MP3 is today's — confirm size > ~200 KB and that
     `~/.hermes/projects/iaahoy/build/podcast.mp3` is fresh).
   - The cover illustration is served: `curl -s -o /dev/null -w '%{http_code} %{size_download}\n' https://jgbarahbot.github.io/iaahoy/assets/lead-illo-<TODAY>.jpg` → 200, ~100–400 KB (skip only if the day published without one).
   - Swap log with the full run: `~/.hermes/gpu-swaps/qwen3-podcast-gpu-swap.log`
     (the target writes `qwen3-podcast-gpu.log`; look for the target reaching
     `PODCAST OK` and `PUBLISH OK`; a `FALLO publish` line means the
     MP3 exists but the push failed → run `python3 scripts/publish.py` from the
     project dir once vLLM is back).
   - Every page's `<audio src=...>` must resolve to `/podcast.mp3`: root uses
     `podcast.mp3`, the permlink and archive use `../podcast.mp3` (they live
     in `editions/`). Check the rendered HTML carries the right relative
     path; the permlink `curl -s <permalink>` should 200.
   - Report the live URL + edition date to the user in Spanish (or their
     language), 2–4 lines: portada headline, 2–3 highlights, and the URL.


## Edition JSON schema (what render.py expects)
```
{
  "date": "27 de septiembre de 2026",      # long Spanish date (masthead)
  "weekday_long": "domingo",               # Spanish weekday
  "edition": "Edición nº 2",              # running number (bump daily)
  "tagline": "IA de pesos abiertos y software libre, cada mañana",
  "lead": {                                  # portada — the one big story
    "title": "…", "summary": "… (4-6 sentences)",
    "illustration": {                        # step 3: cover illustration (moss-image-news-illustration)
      "file": "lead-illo-2026-10-26.jpg",
      "alt": "… Spanish description of the scene …",
      "caption": "Ilustración de la portada, generada con MOSS-Image: …"
    },
    "tags": ["…"], "links": [{"label": "…", "url": "…"}]
  },
  "sections": [
    { "title": "Modelos", "notes": [
      { "title": "… (terms that stay in English *in asterisks*)",
        "summary": "… ONE recap paragraph, same asterisk convention …",
        "body": ["… paragraph 1 …","… paragraph 2 …","… paragraph 3 …"],
        "tags": ["…"],
        "links": [{"label": "GitHub", "url": "…"}] }
    ]},
    { "title": "Agentes libres", "notes": [ … ]},
    { "title": "Software libre para IA", "notes": [ … ]},
    { "title": "Papers e investigación", "notes": [ … ]},
    { "title": "Comunidad y self-hosting", "notes": [ … ]}
  ],

  // NOTE: `body` is a LIST of flowing paragraphs (render.py turns each into
  // a <p>, and converts *term* markers into <em>term</em>). `summary` is a
  // single recap paragraph shown in italics above the body. Both carry the
  // same two-pass asterisk convention. The lead (portada) uses the same
  // summary + body shape.
  "colophon": {
    "title": "IA Abierta Hoy",
    "short_title": "IA*A*Hoy",
    "made_with": [
      "el skill iaahoy-daily-edition (https://github.com/jgbarahbot/iaahoy-daily-edition) — recolección, curado y publicación",
      "el skill espanish-podcast (https://github.com/jgbarahbot/espanish-podcast) — el podcast en audio",
      "el skill moss-image-news-illustration (https://github.com/jgbarahbot/moss-image-news-illustration) — la ilustración de la portada"
    ],
    "fineprint": "Contenido generado automáticamente a partir de fuentes públicas por Hermes, usando <MODELO>, para que lo disfrutes y te sea útil."
  }
}
```
The `made_with` list feeds the "Hecho con Hermes" note at the bottom of the
page (render.py turns each trailing `https://github.com/…/…` URL into a link)
— always keep the THREE skill entries with their repo URLs (iaahoy-daily-edition,
espanish-podcast, moss-image-news-illustration); step 2's curation rule makes
the `colophon` carry them.

## The two-pass Spanish method (how EVERY note is written)

This is the editorial convention the user fixed on 2026-10-24 after the MOSS-Image
note (reference: `NOTA_MOSS-Image_v8.md`). The failure it prevents: writing
Spanish that still carries English phrasing, and then slapping *asterisks* onto
**Spanish** words (because the phrase was inherited from the English source) —
which renders wrong and reads wrong. So notes are produced in **two passes**:

- **Pasa 1 — pure Spanish.** Write the whole note as flowing Spanish, translating
  EVERYTHING that can reasonably be translated. No asterisks at all. Rules:
  - *weights* → **pesos**, *render* → **renderizado**, *layout* → **maquetación**,
    *state-of-the-art* → **el mejor entre…**, *technical report* → **informe técnico**,
    *open-weights* → **pesos abiertos**, *single-file* → **archivo único**, *self-hosting* →
    **self-hosting** (kept — it has no clean Spanish equivalent) or **autalojamiento**,
    *coding* → **codificación/código**, *trending* → **tendencia**, *likes* → **me gusta**,
    *open source* → **código abierto/software libre**. **The user's 2026-10-25
    bar:** common, easily-translatable English words must NOT survive into the
    text — not just in the podcast script, in the notes themselves. It is not
    zero-tolerance (some English slips through, especially for the most
    habitual terms), but the translation effort should be visible: when a
    Spanish reader would naturally say *pesos abiertos* instead of *open
    weights*, that is what the note says.
  - **Unfamiliar acronyms are expanded in parentheses on FIRST use only**: e.g.
    "un transformer de difusión (DiT, de «diffusion transformer»)", "ajuste fino
    supervisado (SFT, de «supervised fine-tuning»)", "LongLongTextBench (LLTB)". After
    the first expansion, use the bare acronym.
  - **No per-paragraph bold headers.** The body is one continuous piece of prose,
    only split into paragraphs (no "**Arquitectura:**"-style lead-ins).
- **Pasa 2 — mark the English.** The ONE change: add *asterisks* around **only the
  terms that genuinely stay in English** (product names, model names, acronyms,
  licenses, tool/framework names — *MOSS-Image*, *DiT*, *Apache 2.0*, *SFT*,
  *ComfyUI*, *vLLM*, *LoRA* …). **Two exclusions (user rule, 2026-10-24):**
    1. *Never* asterisk a word that is spelled the same in Spanish —
       `token`, `multimodal`, `benchmark`, `routing`, `sandbox`, `framework`,
       `stream`, `GPU` (in Spanish too it's "GPU"), `LLM`, etc. are fine plain.
       If it reads as Spanish, it stays plain.
    2. *Never* asterisk a Spanish word, and *never* asterisk a noun you already
       translated in pasa 1 (`renderizado`, `maquetación`, `pesos`…).
  **The test:** if a Spanish reader would write that exact word the same way in
  their own article, it stays plain.

**JSON shape per note:**
- `title` — the pasa-2 title (English terms in *asterisks*).
- `summary` — **exactly ONE paragraph** that recaps the whole note (the "lead" the
  reader can skip the body for). Pasa-2 asterisks.
- `body` — **a list of flowing paragraphs** (the actual article; the lead is 3
  paragraphs, most notes 2–3, a flagship note up to ~6). Each list item becomes a
  `<p>`. Target ~500–600 words for a flagship/lead, ~120–250 for a regular note.
- `tags` — snake_case slugs (unchanged).
- `links` — ≥1, real, technical.

**HTML rendering (render.py `esc_em`):** the asterisks in `title`/`summary`/`body`
are converted to `<em>term</em>` — they render as *styled* foreign terms (weight +
accent color, NOT italic, since the recap already uses italics), never as literal
`*`. A lone unpaired `*` never matches and passes through escaped. The **podcast
script keeps the raw asterisks** — there they are the TTS cue to read a term in
English, so do not "fix" them out of the `.podcast.txt`. Do not hand-write `<em>`
in the JSON; always write the source with asterisks and let `render.py` convert.
Standard section titles (user convention 2026-10-25, adapt to the day's
news): **Modelos**, **Agentes libres**, **Software libre para IA**, **Papers
e investigación**, **Comunidad y self-hosting**. **Agentes libres** holds
free *agents* only (new agents, improvements, agent skills, novel agent
uses); **Software libre para IA** holds the other open-source AI software
(engines, CLIs, runtimes, monitors — no agents). Keep the lead to the single
most important item of the day (up to 700–800 words when it has material).

## Pitfalls (learned)
- **Mobile overflow came from `.chip{white-space:nowrap}`** (2026-10-25, user
  report "el HTML no parece adaptado al móvil"): a chip whose label was a long
  repo slug (`Hugging Face — cuantización GGUF (abenzerps/Spark-X2.6-4B-Quantized)`)
  could not wrap and forced the entire `.featured` subtree (kicker, h2, lead,
  fbody) to 467–487 px, producing horizontal scroll at ≤ ~640 px viewports. Fix:
  `overflow-wrap:anywhere` on `body`, chip `white-space:normal`+`max-width:100%`+
  `word-break:break-word`, `min-width:0` on `.wrap`/`.note`/`.chips`, plus a
  `@media(max-width:480px)` tuning block. Diagnosis technique: serve the built
  HTML locally, set CDP `Emulation.setDeviceMetricsOverride` at several widths,
  and measure `document.documentElement.scrollWidth` vs `clientWidth` + which
  elements' `getBoundingClientRect().width` exceeds the viewport (deepest
  offender = the nowrap token). NOTE the CSS is INLINED into every permlink
  (`editions/*.html`), so any CSS fix must go into `templates/style.css` AND be
  re-rendered + re-published (`publish.py`) to reach the live site; the CDN can
  serve the stale inlined copy for ~60–90 s after a force-push, so verify the
  live bytes with `curl` + a cache-busting `?v=` before concluding it didn't ship.
- `render.py` flags: `--json <edition.json> --css <style.css> --podcast <rel.mp3> --out <html>`; for the archive it's `--list-editions <editions_dir>` (not `--json`). `--podcast` is the RELATIVE path as it should appear in that page. **Masthead (v2.21):** H1 renders as `IA·A·Hoy` (middle dots), the topline says «La IA abierta resumida por una IA abierta», and the dateline nav auto-builds one anchor link per section (slugs generated by `_slug()`, accent-stripped) next to Archivo — the JSON needs no `id`/icon fields for this. The podcast block renders INSIDE the page container with the fixed label «IA·A·Hoy Hablada: un resumen pensado para oírse»; do not hand-build an audio tag in the JSON.
- **`podcast_systemd.sh` needs ABSOLUTE `--script`/`--out` paths (learned 2026-10-14):** the one-shot systemd unit's CWD is NOT the project dir, so relative `editions/…` paths die instantly with `FileNotFoundError` (exit 1 in ~30 ms, 300 KB mem — NOT an OOM). Always pass `~/.hermes/projects/iaahoy/editions/<TODAY>.podcast.txt` and `~/.hermes/projects/iaahoy/build/podcast.mp3`. To see the REAL error (the launcher's `runs/podcast-*.log` only holds `systemd-run --wait`'s status), use `journalctl --user -u iaahoy-podcast.service --no-pager -n 40`.
- **NEVER run TTS synthesis inside a Hermes worker (learned 2026-10-14/19):**
  any real engine (CosyVoice3, Qwen3-TTS CPU, VoiceDesign) needs more than the
  4 GiB worker cgroup cap (`process_registry._WORKER_MEMORY_MAX_CAP_BYTES`) and
  OOM-137s in a `terminal`/`execute_code` call (background OR foreground both
die; `OMP_NUM_THREADS` does not help — it's model weights, not thread
  stacks). The ONLY safe ways: (a) the GPU swap (a detached `systemd-run`
  job — step 4) or (b) a detached systemd unit like `podcast_systemd.sh`
  (`MemoryMax=8G`) / foreground from the gateway scope. The `--engine piper`
  path is the only one that fits inside the 4 GiB worker cap and is the
  in-worker last-resort fallback. Engine-specific OOM numbers, venv quirks
  and the 12 GiB unit for Qwen3-TTS CPU are in the `espanish-podcast` skill.
- `make_podcast.py` canonical copy lives in `~/.hermes/skills/espanish-podcast/scripts/` (project copy is kept in sync); flags: `--script <podcast.txt> --out <podcast.mp3> --engine {qwen,qwen-syn,cosy,piper}` (default `qwen` = Qwen3-TTS voice-clone; `qwen-syn` = Qwen3-TTS VoiceDesign synthetic; `cosy` = CosyVoice3 emotion; `piper` = CPU fallback; plus `--only S E`, `--assemble`, `--clean`). Engine, worker protocol, emotion and all TTS pitfalls are documented in the `espanish-podcast` skill — keep that boundary, don't re-document TTS here.
- English-IPA mechanism (do NOT "fix" it): piper's `[[…]]` blocks are split **char-by-char** (`voice.py`: `extend(text_part[2:-2].strip())`) and each char is looked up in the model's phoneme id-map, unknowns skipped silently. piper's own `;en` inline switch does NOT work (phonemize_espeak strips (lang) flags, L40) — the working path is pre-phonemizing the term with espeakbridge (`EspeakPhonemizer()` to init, then `set_voice("en-us")`, `get_phonemes(term)`) and wrapping the IPA in `[[…]]`. espeakbridge without prior init segfaults.
- The archive page lives in `editions/`, so its podcast link MUST be `../podcast.mp3` (publish.py already does this); if you ever hand-render the archive, use `../podcast.mp3`.
- HF blog HTML is JS-rendered → use RSS `desc` (often empty) + `web_search` to ground the lead story, not raw HTML scrape.
- GitHub Pages first deploy needs a build; don't conclude failure on first 404.
- `publish.py` already self-heals `git/` and flattens history; only `rm -rf git` manually if it still misbehaves. Never commit the secret; it's injected into the clone URL only.
- Bump the `edition` running number from the latest prior edition (count `editions/*.json`).
- If the day's news is thin (weekend), still publish — reuse trending models/repos with fresh framing; never skip a day.
- Redaction layer: never type the literal word for the secret (lowercase) in tool-call strings — it gets rewritten; use the env var name or `chr()` construction in code.

- **Nunca el wrapper del swap en foreground de una llamada a tool del agente** (2026-10-19 01:21): el timeout de la llamada lo mato con SIGKILL (no atrapable) antes de que el trap hiciese el ON; vLLM quedo caido 01:21-08:40 (hasta el reboot del usuario), el cron de 08:30 fallo en silencio y se perdio la edicion del dia. El wrapper solo se lanza con `systemd-run --user` (step 4), y el cron empieza con el pre-flight de salud de vLLM (step 0).
- **Un `podman start hyperqwen` a secas (sin `hyperqwen_on.sh`) puede dejar un zombi** (contenedor Up, modelo no sirve; sin crash en systemd que lo detecte). Si vLLM no responde, usar siempre `hyperqwen_on.sh` (rama zombie + check de chat/completions + flock), nunca un `podman start` directo.
- **Calidad del MP3 del podcast (2026-10-19, bugs encontrados por el usuario y verificados con faster-whisper):** el worker clona `refA.wav`/`refC.wav` literalmente, así que **antes de sintetizar comprueba que los refs que usa el engine activo son los del usuario** — para el engine por defecto Qwen3-TTS eso son `~/.hermes/cache/qwen3-tts/refA.wav` (voz del usuario, ~12 s) y `refC.wav` (femenina, ~8 s); para CosyVoice (`--engine cosy`) son `~/.hermes/cache/cosyvoice/refA.wav`/`refC.wav` (deben coincidir en md5 con `ref_user.wav` / `ref_F.wav`). **Después de cada MP3, transcribe el primer y el último bloque** (faster-whisper medium, venv Python 3.14 en `/home/jgb/.hermes/installs/d6a27a1debcdb2b5/environments/87801bca3da147548792a18b93c00f82/venv/bin/python`) y verifica que no aparezca texto en inglés. Con el engine por defecto (Qwen3-TTS clone) NO hay canal de instrucción, así que no debe haber NINGÚN inglés; si lo hay es un bug del worker. (El bug histórico de `inference_instruct2` — la frase en inglés leída en voz alta — era específico de CosyVoice `--engine cosy`, donde la instrucción debe llevar el prefijo `You are a helpful assistant. …<|endofprompt|>`; ver el skill `espanish-podcast` para el detalle del formato y de ese prefijo.)
- **The illustration is integrated BEFORE the podcast swap** (2026-10-26):
  the podcast swap's publish renders from the edition JSON, so
  `lead.illustration` must already be in the JSON when step 5 launches —
  one publish then ships image + audio together. Setting it afterwards
  would require a second publish. If MOSS fails, omit the field and publish
  without the figure (render.py handles its absence).
- **No vision on the local LLM for MOSS outputs** (2026-10-26):
  `vision_analyze` returns 400 on the generated images, so the user picks
  among the seeds — or, if they do not express a preference, default to the
  first seed's image. Never claim to have "checked" the image content; you
  cannot.
## Cron (three-stage self-healing chain, v2.24.0)
The daily flow is split across **three scheduled one-shot jobs** because the
two GPU swaps (MOSS step 3, podcast step 5) each take vLLM offline — and
with it the agent's own LLM — so no single session can cross both. Each stage
is its own scheduled trigger: a stall in one is picked up by the next. This
chain was added on 2026-10-27 after the 08:30 one-shot ended its turn after
the MOSS swap and nothing woke it for 24 h (the edition sat unpublished until
it was finished manually).

- **08:30 — `iaahoy-daily-edition`** (job `3c49b1337e9c`, deliver: matrix
  home channel): steps 0–3 — vLLM pre-flight, collect, curate
  `editions/<TODAY>.json`, launch the MOSS cover swap, **end turn**. Its
  final response is only a note that the swap is running.
- **10:00 — `iaahoy-continuation`** (job `cc78349fa90e`, deliver: local):
  vLLM is back. IDEMPOTENT finish: if the edition is already live (permalink
  200 + fresh MP3) report and stop; otherwise integrate the cover image if
  `lead.illustration` is missing (first seed's PNG → JPEG, step 3.5), write
  the podcast script if missing (step 4), launch the podcast+publish swap
  (step 5), **end turn**.
- **10:45 — `iaahoy-verify`** (job `2a1b79015a05`, deliver: matrix home
  channel): vLLM is back. Verify the live site (root 200, permalink 200,
  `podcast.mp3` fresh > ~200 KB matching the local build mtime, cover 200,
  swap log `PODCAST OK` + `PUBLISH OK`). If good → deliver the day's 2–4
  line Spanish summary (edition date + nº, portada headline, 2–3
  highlights, live URL) — **the user's daily message comes from THIS job,
  not from the 08:30 one**. If not live → recover with the GPU-free CPU path
  (`podcast_systemd.sh` + `publish.py`), re-verify, then deliver the summary
  (noting recovery); after two failed attempts, deliver a plain Spanish
  notice that the edition did not ship, with the error.

**The swap is the ONLY publish path — never run `publish.py` by itself before
the MP3 exists.** The job's cron prompt used to list "5 steps"
(collect → curate → render → `publish.py` → verify) with the podcast-swap
step only implicit, so on 2026-10-23 the agent read it as "just those 5 steps",
ran `publish.py` without synthesizing anything, and shipped TODAY's HTML with
YESTERDAY's MP3 (the site's single `podcast.mp3` slot still held the 10-22
audio). The prompt now states the binding order explicitly (write the
`.podcast.txt`, launch the detached GPU swap — which renders AND publishes —
END your turn; verify in a later turn). If you are ever handed a "5-step"
prompt again that says "publish" but never mentions the swap, STOP: that is
the 2026-10-23 shape and publishing there repeats the bug — run the swap
first, publish only via it.
Since v2.23.0 (2026-10-26) the flow has TWO detached swaps and TWO end-turn
points: the MOSS illustration swap (step 3) first, then — after integrating
the image and writing the script — the podcast swap (step 5). The agent
ends its turn after each swap; since v2.24.0 (2026-10-27) each end-turn is
resumed by the next SCHEDULED stage of the three-stage cron chain above
(10:00 continuation, 10:45 verify) — never by waiting for a user message,
because a one-shot 08:30 job has no other trigger for 24 h (the 2026-10-27
stall). If the illustration batch fails twice, skip the
integration (no `lead.illustration`) and proceed straight to the podcast
swap — the edition must publish regardless.

## Keeping this skill in sync with GitHub
This directory is a git repo tracking `jgbarahbot/iaahoy-daily-edition`. After any local edit, run `./sync.sh` (commits, fast-forwards, and pushes using `GITHUB_CONTENT_RW_TOKEN` from `~/.hermes/.env`).

