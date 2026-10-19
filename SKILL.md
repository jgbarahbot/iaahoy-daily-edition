---
name: iaahoy-daily-edition
description: "iaahoy: produce + publish daily Spanish open-AI newspaper."
version: 2.5.0
author: jgbarah
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [iaahoy, daily-newspaper, github-pages, open-ai, spanish, cron, podcast]
    requires_skills: [espanish-podcast]
    related_skills: [news-digest, github-repo-management, hyperqwen-gpu-swap, espanish-podcast]
---

# ia·ahoy — daily open-AI newspaper + podcast (Spanish)

**Podcast synthesis runs on the GPU** (step 4) via the `hyperqwen-gpu-swap`
skill: a detached systemd user job stops the HyperQwen vLLM container,
synthesizes the script with CosyVoice3 in fp32 on the RTX 3090
(`cosyvoice:gpu` container) and restarts vLLM. (fp32 since 2026-10-19:
fp16 accumulated rounding error in long autoregressive blocks, drifting F0
upward and turning Spanish into English-accented speech — user-identified.)
The script format, the
English-term pronunciation rules and the CPU fallback
(`espanish-podcast` skill, `make_podcast.py`) stay as documented there.
Install the podcast skill first (it is the fallback):
`hermes skills install github.com/jgbarahbot/espanish-podcast`.

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
  - (podcast audio is synthesized in step 4: GPU path via
                                `scripts/podcast_gpu.py` + `gpu_worker.py` in
                                the `cosyvoice:gpu` container, or the CPU
                                `make_podcast.py` fallback from
                                `espanish-podcast`)
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
- TTS: DELEGATED to the `espanish-podcast` skill — it owns the script format,
  the two-voice Piper pipeline (A = `es_ES-davefx-medium`, C =
  `es_MX-claude-high`, both 22050 Hz, user-fixed pair "usa solo a y c"),
  English-term pronunciation (dictionary + numbers-in-Spanish + espeak IPA
  fallback) and all TTS requirements/pitfalls. This skill only WRITES the
  script; synthesis runs in step 4 (GPU by default, `espanish-podcast`'s
  `make_podcast.py` as fallback). After a podcast run, relay any
  `UNSURE: <term>` lines the script prints to the user (they are
  pronunciation candidates for `pron_dict.json`).

## The 5-step pipeline (run in order)

Steps 3–4 split the podcast work: THIS skill writes the script (step 3, LLM);
step 4 synthesizes it with the `hyperqwen-gpu-swap` skill (GPU, CosyVoice3
fp32 — see that skill for the swap mechanism) and falls back to the
`espanish-podcast` skill's `make_podcast.py` (CPU). Load
`hyperqwen-gpu-swap` (and `espanish-podcast` for the fallback) before the
first run of the day.
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
   each with `title` + 2–4 `notes`. Each note: `title`, `summary` (2–4 Spanish
   sentences), `tags` (list), `links` (list of {label,url} — ≥1, prefer
   technical). Use REAL URLs from material; if a summary needs grounding and
   the RSS desc is empty, use `web_search` to verify facts. No placeholder
   links — every URL must be real. **The `colophon` block MUST carry**:
   `title: "IA Abierta Hoy"`, `short_title: "IA*A*Hoy"`, and a `fineprint`
   string in the form:
   `Contenido generado automáticamente a partir de fuentes públicas por Hermes, usando <MODELO>, para que lo disfrutes y te sea útil.`
   where `<MODELO>` is the LLM actually generating it (e.g. "Qwen3.8-27B").
   It MUST also carry the `made_with` list (the two skill names with their
   GitHub repo URLs, see the schema) — it renders the "Hecho con Hermes" note.
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
   English terms, not Spanish words. For emotion: put the English
   instruction in the marker tag of the few blocks that need it
   (`A [Speak cheerfully and loud]: ...`), all other blocks plain `A:`/`C:`
   (neutral). Never write Spanish words in the tags.
4. **Podcast audio — GPU swap: CosyVoice3 on the GPU (fp32), then render +
   publish inside the same swap** (deterministic, ~3–4 min total, ~35× faster
   than the CPU path):
   `systemd-run --user --unit=gpu-swap-iaahoy-podcast --property=TimeoutStartSec=0 --property=KillMode=process bash ~/.hermes/gpu-swaps/iaahoy-podcast-gpu-swap.sh /home/jgb/.hermes/projects/iaahoy/editions/<TODAY>.podcast.txt /home/jgb/.hermes/projects/iaahoy/build/podcast.mp3`
   **REGLA DURO — SOLO via systemd-run (incidente 2026-10-19 01:21:
   vLLM caido ~7 h, edicion perdida):** NUNCA lanzar el wrapper como
   hijo de una llamada `terminal`/`execute_code` del agente: esas
   llamadas tienen un timeout duro que, al llegar, manda SIGKILL al
   arbol de procesos — SIGKILL no se puede atrapar, asi que el
   `trap cleanup` del wrapper (el que haria el ON) NUNCA corrio y el
   modelo no volvio hasta que el usuario dio el reboot. `systemd-run
   --user` desacopla el job del arbol de procesos y grupo de procesos
   del agente: sobrevive a la muerte del agente (que durante el OFF
   pierde su LLM de todos modos). Para una prueba que no toque el
   sitio, anadir `--no-publish` como 3er arg (el target solo
   sintetiza el MP3; el sitio y el git no se mueven).
   **What it does** (see the `hyperqwen-gpu-swap` skill for the mechanism):
   1. ~20 s margin, then **OFF**: stops the HyperQwen vLLM container
      (frees the ~22.5 GB VRAM on the single RTX 3090).
   2. **TARGET**: `iaahoy-podcast-gpu-target.sh` — starts the
      `cosyvoice:gpu` container (conditional driver-lib mounts, 5
      `--device` nodes), copies in `gpu_worker.py` (source of truth:
      `~/.hermes/cache/cosyvoice/docker-build/gpu_worker.py`),
      `podcast_gpu.py` (project scripts/), the day's script and the
      `pron_dict.json`; runs `podcast_gpu.py` inside it: parses the
      two-voice script, synthesizes every block with CosyVoice3 in **fp32
       on the GPU** (RTF ~0.5, ~2–3 s per block; fp32 is the production
       default — fp16 drifted F0 into English accent on long blocks;
       `COSYVOICE_FP16=1` in the env forces fp16 for experiments),
       assembles the MP3 with ffmpeg. Then, still inside the target (the agent is dead during the
      OFF, so the deterministic tail must run here): `publish.py`
      re-renders every edition, copies the MP3 to the site root, and
      force-pushes the flattened history.
   3. **ON**: restarts the vLLM container and waits until the
      `/health` endpoint answers (agent is usable again).
   **Emotion instructions are English-only and short** ("Speak in a
   … tone." / "Talk …" patterns, e.g. "Speak cheerfully and loud") —
   CosyVoice3's `instruct2` is English-tuned; long or Spanish
   instructions leak into the audio. Write the English instruction
   DIRECTLY in the script tag: `A [Speak cheerfully and loud]: ...` —
   the worker's `resolve_instruct()` passes it through verbatim. Spanish
   keys (alegre, cierre, …) still work as an indirection into the
   `INSTRUCT` dict, but raw English is the preferred, unambiguous form.
   Use sparingly: openings/closings and at most one dramatic beat; a
   news digest is mostly neutral.
   **Acento inglés en un bloque = fp16, no el guion (2026-10-19):** el blk_06 de la
   edición 10-18 salió con acento inglés (F0 mediana 214 Hz, derivando a ~272; refs C: 182-195):
   `gpu_worker.py` corría fp16 en el contenedor y fp16 deriva el F0 en bloques largos (>~20 s).
   fp32 (worker CPU, mismo código) dio el texto idéntico limpio → producción ahora es fp32:
   `podcast_gpu.py` hereda `COSYVOICE_FP16` del env (default "0") y el target exporta
   `COSYVOICE_FP16=0`. Prueba rápida de deriva: F0 por bloque (wavs en `build/wavs/wavs/`,
   doble anidado) — C en 182-195, A en ~100; >200 = deriva.: openings/closings and at most one dramatic beat; a
   news digest is mostly neutral.
   **You MUST end your turn right after launching the swap**: you lose
   your LLM in the OFF phase; the systemd job is detached (the agent can
   die, the chain finishes and vLLM comes back). When you're alive again
   (a later user message or your scheduled turn), verify in **step 5**.
   **Fallback (no GPU available / swap fails twice):** the old CPU path —
   `bash ~/.hermes/projects/iaahoy/scripts/podcast_systemd.sh --script … --out …`
   (CosyVoice3 CPU via `make_podcast.py`, ~25–35 min; then run
   `scripts/render.py` and `scripts/publish.py` from the project dir manually).
   Only if that also OOMs, `--engine piper`.
5. **VERIFY the published site** (run after the swap completes, i.e. in a
   later turn when vLLM is back — do not trust the swap's exit code alone).
   The swap already did render+publish inside the target, so this is
   check-only:
   - `curl -s -o /dev/null -w '%{http_code} %{size_download}\n' https://jgbarahbot.github.io/iaahoy/` → 200.
   - Pages first build takes ~30–60 s after a push; poll once if it 404s.
   - `curl -s -o /dev/null -w '%{http_code}\n' https://jgbarahbot.github.io/iaahoy/podcast.mp3` → 200
     (the MP3 is today's — confirm size > ~200 KB and that
     `~/.hermes/projects/iaahoy/build/podcast.mp3` is fresh).
   - Swap log with the full run: `~/.hermes/gpu-swaps/iaahoy-podcast-gpu-swap.log`
     (look for `PODCAST OK` and `PUBLISH OK`; a `FALLO publish` line means the
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
    "made_with": [
      "el skill iaahoy-daily-edition (https://github.com/jgbarahbot/iaahoy-daily-edition) — recolección, curado y publicación",
      "el skill espanish-podcast (https://github.com/jgbarahbot/espanish-podcast) — el podcast en audio"
    ],
    "fineprint": "Contenido generado automáticamente a partir de fuentes públicas por Hermes, usando <MODELO>, para que lo disfrutes y te sea útil."
  }
}
```
The `made_with` list feeds the "Hecho con Hermes" note at the bottom of the
page (render.py turns each trailing `https://github.com/…/…` URL into a link)
— always keep the two skill entries with their repo URLs.
Suggested section titles (adapt to the day's news): **Modelos**, **Agentes y
software**, **Papers e investigación**, **Comunidad y self-hosting**. Keep the
lead to the single most important item of the day.

## Pitfalls (learned)
- `render.py` flags: `--json <edition.json> --css <style.css> --podcast <rel.mp3> --out <html>`; for the archive it's `--list-editions <editions_dir>` (not `--json`). `--podcast` is the RELATIVE path as it should appear in that page.
- **`podcast_systemd.sh` needs ABSOLUTE `--script`/`--out` paths (learned 2026-10-14):** the one-shot systemd unit's CWD is NOT the project dir, so relative `editions/…` paths die instantly with `FileNotFoundError` (exit 1 in ~30 ms, 300 KB mem — NOT an OOM). Always pass `~/.hermes/projects/iaahoy/editions/<TODAY>.podcast.txt` and `~/.hermes/projects/iaahoy/build/podcast.mp3`. To see the REAL error (the launcher's `runs/podcast-*.log` only holds `systemd-run --wait`'s status), use `journalctl --user -u iaahoy-podcast.service --no-pager -n 40`.
- **CosyVoice venv `bin/python` symlinks can be stripped:** if the unit fails in ~30 ms, check `~/.hermes/venvs/cosyvoice/bin/python` — if the `python`/`python3`/`python3.11` symlinks are gone, restore them to the base from `pyvenv.cfg` (`executable =`), e.g. `ln -sf <base> bin/python3.11 && ln -sf python3.11 bin/python3 && ln -sf python3.11 bin/python`.
- **CosyVoice3 inside any Hermes worker = OOM 137 (learned the hard way):** the
  worker cgroup cap is 4 GiB and the model needs ~4.2 GiB RSS; `OMP_NUM_THREADS`
  does NOT help (it's the model weights, not thread stacks). ALWAYS run
  CosyVoice synthesis through `podcast_systemd.sh` (MemoryMax=8G) or foreground
  from the gateway scope. A background/foreground `terminal` call both die.
- `make_podcast.py` canonical copy lives in `~/.hermes/skills/espanish-podcast/scripts/` (project copy is kept in sync); flags: `--script <podcast.txt> --out <podcast.mp3> --engine {cosy,piper}` (default `cosy`, `--only S E`, `--assemble`, `--clean`). Voice details, CosyVoice worker protocol, emotion instructions and TTS pitfalls are documented in the `espanish-podcast` skill — keep that boundary, don't re-document TTS here.
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
- **Calidad del MP3 del podcast (2026-10-19, dos bugs encontrados por el usuario y verificados con faster-whisper):** (1) `refA.wav`/`refC.wav` en `~/.hermes/cache/cosyvoice/` estaban apuntando a clones viejos de Piper (davefx, acento inglés) en vez de las muestras del usuario — el worker clona `refA`/`refC` literalmente, así que **antes de sintetizar comprueba que `refA.wav` = `ref_user.wav` (12 s, voz del usuario) y `refC.wav` = `ref_F.wav` (6.85 s, femenina)** (md5 debe coincidir). (2) `inference_instruct2` requiere el prefijo oficial `You are a helpful assistant. <instr><|endofprompt|>`; sin él la frase en inglés se lee en voz alta al inicio del bloque (se oía "cheerfully and la" en la edición 10-18). **Después de cada MP3, transcribe el primer y el último bloque** (faster-whisper medium, venv Python 3.14 en `/home/jgb/.hermes/installs/d6a27a1debcdb2b5/environments/87801bca3da147548792a18b93c00f82/venv/bin/python`) y verifica que no aparezca texto en inglés. Ver skill `espanish-podcast` para el detalle del formato.
## Cron
The daily 08:30 job (08:30 CEST) fires this exact flow. When you run it, your
FINAL RESPONSE is delivered to the user — write a 2–4 line Spanish summary:
edition date, the portada headline, 2–3 other highlights, and the live URL.

## Keeping this skill in sync with GitHub
This directory is a git repo tracking `jgbarahbot/iaahoy-daily-edition`. After any local edit, run `./sync.sh` (commits, fast-forwards, and pushes using `GITHUB_CONTENT_RW_TOKEN` from `~/.hermes/.env`).

