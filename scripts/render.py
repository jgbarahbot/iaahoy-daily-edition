#!/usr/bin/env python3
"""iaahoy render engine (v5).

Reproduces the canonical site structure (masthead / paper / aside / colophon —
the class scheme templates/style.css was written for) from an edition JSON,
inlining the CSS so every page is a self-contained file. Adds three features:
  * a podcast CTA at the top ("Si prefieres escuchar en lugar de leer…")
  * a Creative-Commons BY-SA 4.0 license block at the bottom (self-contained badge)
  * the fineprint carries the generating model name (read from the JSON colophon)

CLI (used by publish.py):
  render.py --json <edition.json> --css <style.css> --out <page.html> \
            [--podcast <relative-url-to-podcast.mp3>]
  render.py --editions <editions/index.json> --css <style.css> --out <editions/index.html>
            [--podcast <relative-url-to-podcast.mp3>]

The podcast URL is relative: "podcast.mp3" on the root page, "../podcast.mp3"
on edition permalinks / the archive (a GitHub project site cannot use root-absolute paths).
"""
import argparse
import html
import json
import os
import re
from pathlib import Path

CC_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
DATE_JSON_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
CC_NAME = "Creative Commons Atribución-CompartirIgual Internacional 4.0"
CC_TITLE = "Creative Commons Atribución-CompartirIgual 4.0 Internacional"


def esc(s):
    return html.escape(str(s), quote=True)


def render_chips(links, tags, source):
    out = []
    for lk in links or []:
        out.append('<a class="chip link" href="%s" rel="noopener">%s</a>' % (esc(lk["url"]), esc(lk["label"])))
    for t in tags or []:
        out.append('<span class="chip">%s</span>' % esc(t))
    if source:
        out.append('<span class="chip src">vía %s</span>' % esc(source))
    if not out:
        return ""
    return '<div class="chips">' + "".join(out) + "</div>"


def render_lead(lead, base):
    if not lead:
        return ""
    title = esc(lead.get("title", ""))
    url = esc((lead.get("links") or [{}])[0].get("url", "#"))
    body = "".join("<p%s>%s</p>" % (' class="dropcap"' if i == 0 else "", esc(p)) for i, p in enumerate(lead.get("body", [])))
    h = '<div class="featured">'
    h += '<p class="kicker">%s</p>' % esc(lead.get("kicker", "Portada"))
    h += '<h2><a href="%s" style="color:inherit;text-decoration:none" rel="noopener">%s</a></h2>' % (url, title)
    h += '<p class="lead">%s</p>' % esc(lead.get("summary", ""))
    h += '<div class="fbody">%s</div>' % body
    h += render_chips(lead.get("links"), lead.get("tags"), lead.get("source"))
    h += "</div>"
    return h


def render_note(note):
    links = note.get("links") or []
    url = links[0]["url"] if links else "#"
    spec = '<p class="spec">%s</p>' % esc(note.get("spec", "")) if note.get("spec") else ""
    body = "".join("<p>%s</p>" % esc(p) for p in note.get("body", []))
    h = '<article class="note">'
    h += '<h4><a href="%s" rel="noopener">%s</a></h4>' % (esc(url), esc(note.get("title", "")))
    h += spec + body
    h += render_chips(links, note.get("tags"), note.get("source"))
    h += "</article>"
    return h


def render_section(sec):
    notes = "".join(render_note(n) for n in sec.get("notes", []))
    blurb = '<p class="sec-blurb">%s</p>' % esc(sec.get("blurb", "")) if sec.get("blurb") else ""
    h = '<section class="block" id="%s">' % esc(sec.get("id", ""))
    h += '<div class="sec-head"><span class="icon">%s</span><h3>%s</h3><span class="rule"></span></div>' % (esc(sec.get("icon", "")), esc(sec.get("title", "")))
    h += blurb + notes + "</section>"
    return h


def render_trending(trending):
    if not trending:
        return ""
    items = "".join(
        '<div class="repo">'
        '<a class="name" href="%s" rel="noopener">%s</a>'
        '<span class="stars">%s</span>'
        '<div class="desc">%s</div>'
        '<div class="meta">%s</div>'
        "</div>" % (
            esc(r.get("url", "#")),
            esc(r.get("name", "")),
            esc(r.get("stars", "")),
            esc(r.get("desc", "")),
            esc(r.get("meta", "")),
        )
        for r in trending
    )
    return '<div class="aside-block"><h5>Repos en tendencia<span class="rule"></span></h5>' + items + "</div>"


def render_papers(papers):
    if not papers:
        return ""
    items = "".join(
        '<li><a href="%s" rel="noopener">%s</a><span class="au">%s</span></li>'
        % (esc(p.get("url", "#")), esc(p.get("title", "")), esc(p.get("authors", "")))
        for p in papers
    )
    return '<div class="aside-block"><h5>Papers del día · Hugging Face<span class="rule"></span></h5><ul class="papers">%s</ul></div>' % items


def render_community(community):
    if not community:
        return ""
    items = "".join(
        '<li>'
        '<div class="src">%s</div>'
        '<a href="%s" rel="noopener">%s</a>'
        '<div class="note-txt">%s</div>'
        "</li>" % (esc(c.get("src", "")), esc(c.get("url", "#")), esc(c.get("title", "")), esc(c.get("note", "")))
        for c in community
    )
    return '<div class="aside-block"><h5>Comunidad en ebullición<span class="rule"></span></h5><ul class="community">%s</ul></div>' % items


def render_podcast_cta(url):
    if not url:
        return ""
    h = '<div class="podcast-cta">'
    h += "<strong>🎧 Si prefieres escuchar en lugar de leer…</strong>"
    h += "<p>La edición de hoy en audio. Dale al play: un resumen pensado para oírse, con la voz de la casa.</p>"
    h += '<audio controls preload="none" src="%s"></audio>' % esc(url)
    h += '<p class="podcast-note"><span class="short">IA*A*Hoy</span> en corto — solo está disponible la edición de <span class="today">hoy</span>: el audio anterior no se conserva.</p>'
    h += "</div>"
    return h


def render_cc_license():
    badge = (
        '<a class="cc-badge" href="%s" target="_blank" rel="license noopener" title="%s">'
        '<span class="cc-circ">CC</span><span class="cc-circ letter"><b>BY</b></span>'
        '<span class="cc-circ squared"><span>SA</span></span>'
        "</a>" % (CC_URL, CC_TITLE)
    )
    name = '<a class="cc-name" href="%s" target="_blank" rel="license noopener">%s</a>' % (CC_URL, CC_NAME)
    return '<div class="license">' + badge + name + "</div>"


def _linkify_repo(s):
    """Turn a github.com/<user>/<repo> URL inside a string into a link.

    Matches the first GitHub repo URL and links it; the match stops at a
    closing paren, whitespace or end-of-string so it works in both the
    "el skill x (https://github.com/u/r) — desc" and bare-URL forms."""
    m = re.search(r"https?://github\.com/[\w.-]+/[\w.-]+?(?=[\s)\]]|$)", s)
    if not m:
        return esc(s)
    url = m.group(0).rstrip(")\]")
    return (esc(s[:m.start()])
            + '<a href="%s" rel="noopener">%s</a>' % (esc(url), esc(url))
            + esc(s[m.end():]))


def render_made_with(col):
    """'Hecho con Hermes' note: credits Hermes + the skills that built this."""
    items = col.get("made_with") or []
    if not items:
        return ""
    lis = "".join("<li>%s</li>" % _linkify_repo(x) for x in items)
    return ('<p class="made-with"><b>Hecho con Hermes</b> — este diario se genera '
            "automáticamente gracias a estos skills:<ul class=\"made-list\">%s</ul></p>" % lis)


def render_colophon(col, base):
    about = esc(col.get("about", ""))
    srcs = " · ".join(esc(s) for s in col.get("sources", []))
    fine = esc(col.get("fineprint", ""))
    h = '<footer class="colophon"><div class="wrap"><h6>El colofón</h6><div class="cols"><div>'
    h += about
    h += '</div><div><b>Fuentes de esta edición</b><br>%s</div></div>' % srcs
    h += render_made_with(col)
    h += '<p class="fineprint">%s</p>' % fine
    h += render_cc_license()
    h += "</div></footer>"
    return h


def render_masthead(ed, base):
    prev_nav = ""
    if ed.get("prev"):
        prev_nav += '<a href="%s">← Anterior</a>' % esc(ed["prev"])
    if ed.get("next"):
        prev_nav += '<a href="%s">Siguiente →</a>' % esc(ed["next"])
    if base == "editions":
        archive = "../editions/index.html"
    else:
        archive = "editions/index.html"
    nav = prev_nav + '<a href="%s">Archivo</a>' % archive
    h = '<header class="masthead"><div class="wrap">'
    h += '<div class="topline"><span>La prensa de la IA abierta</span><span>Edición en línea · 100% estática</span></div>'
    h += '<h1>ia<span class="amp">·</span>ahoy</h1>'
    h += '<p class="tagline">IA Abierta Hoy — pesos abiertos, kernels, agentes y fine-tunes: lo que suena, lo que estrena y lo que empieza a importarte.</p>'
    h += '<div class="dateline"><span><span class="ed">%s</span> &nbsp;·&nbsp; %s %s &nbsp;·&nbsp; %s</span><nav>%s</nav></div></div></header>' % (
        esc(ed.get("edition", "Edición")), esc(ed.get("weekday_long", "")), esc(ed.get("date", "")), esc(ed.get("place", "")), nav
    )
    return h


def build_page(ed, css, podcast_url, base):
    aside = ed.get("aside", {})
    sections = "".join(render_section(s) for s in ed.get("sections", []))
    aside_html = (
        '<div class="aside">'
        + render_trending(aside.get("trending"))
        + render_papers(aside.get("papers"))
        + render_community(aside.get("community"))
        + "</div>"
    )
    parts = [
        "<!doctype html>",
        '<html lang="es"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>IA Abierta Hoy (ia·ahoy) — %s</title>" % esc(ed.get("date", "")),
        '<meta name="description" content="Edición diaria de IA Abierta Hoy: pesos abiertos, kernels, agentes y self-hosting. %s">' % esc(ed.get("edition", "")),
        '<link rel="alternate" type="application/json" href="%seditions/%s">' % ("../" if base == "editions" else "", esc(ed.get("_file", ""))),
        "<style>" + css + "</style></head><body>",
        render_masthead(ed, base),
        render_podcast_cta(podcast_url),
        '<main class="wrap">',
        render_lead(ed.get("lead"), base),
        '<div class="paper"><div class="main">' + sections + "</div>" + aside_html + "</div>",
        "</main>",
        render_colophon(ed.get("colophon", {}), base),
        "</body></html>",
    ]
    return "\n".join(parts)


def build_editions_index(editions, css, podcast_url):
    """editions: list of dicts {file, edition, weekday_long, date, lead_title}"""
    items = []
    for e in editions:
        lead = esc(e.get("lead_title", ""))
        date_label = e.get("weekday_long", "") + " " + e.get("date", "")
        li = '<li><a href="%s">%s</a><span class="ed">%s · %s</span>%s</li>' % (
            esc(e["file"]),
            esc(e["file"].split("/")[-1]),
            esc(e.get("edition", "")),
            esc(date_label),
            (" — " + lead) if lead else "",
        )
        items.append(li)
    h = '<!doctype html><html lang="es"><head><meta charset="utf-8">'
    h += '<meta name="viewport" content="width=device-width,initial-scale=1">'
    h += "<title>IA Abierta Hoy (ia·ahoy) — Archivo</title>"
    h += "<style>" + css + "</style></head><body>"
    h += render_masthead({"edition": "Archivo", "date": "todas las ediciones", "place": "GitHub Pages"}, "editions")
    h += render_podcast_cta(podcast_url)
    h += '<main class="wrap"><div class="paper"><div class="main">'
    h += '<section class="block"><div class="sec-head"><span class="icon">🗂️</span><h3>Archivo de ediciones</h3><span class="rule"></span></div>'
    h += '<p class="sec-blurb">Cada día a las 08:30 (CEST) sale una nueva. Las antiguas quedan como enlace permanente.</p>'
    h += '<ul class="editions-list">' + "".join(items) + "</ul>"
    h += "</section></div></div></main>"
    h += render_colophon({
        "about": "IA Abierta Hoy (ia·ahoy): archivo de ediciones diarias de IA abierta.",
        "sources": [],
        "made_with": [
            "el skill iaahoy-daily-edition (https://github.com/jgbarahbot/iaahoy-daily-edition) — recolección, curado y publicación",
            "el skill espanish-podcast (https://github.com/jgbarahbot/espanish-podcast) — el podcast en audio",
        ],
        "fineprint": "Contenido generado automáticamente a partir de fuentes públicas por Hermes.",
    }, "editions")
    h += "</body></html>"
    return h


def editions_from_dir(dirpath):
    """Scan a directory for YYYY-MM-DD.json edition files; return archive
    entries (newest first) in the shape build_editions_index expects."""
    out = []
    for fn in os.listdir(dirpath):
        if not DATE_JSON_RE.match(fn):
            continue
        jf = os.path.join(dirpath, fn)
        try:
            e = json.loads(Path(jf).read_text(encoding="utf-8"))
        except Exception:
            continue
        lead = (e.get("lead") or {}).get("title", "")
        out.append({
            "file": fn[:-5] + ".html",
            "edition": e.get("edition", "Edición"),
            "weekday_long": e.get("weekday_long", ""),
            "date": e.get("date", fn[:-5]),
            "lead_title": lead,
        })
    out.sort(key=lambda x: x["file"], reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--css", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--podcast", default=None, help="relative URL to podcast.mp3 from this page")
    ap.add_argument("--list-editions", default=None, help="directory of YYYY-MM-DD.json -> build the archive page")
    ap.add_argument("--editions", default=None, help="editions/index.json -> build the archive page")
    ap.add_argument("--base", default="root", choices=["root", "editions"], help="page location (for link paths)")
    args = ap.parse_args()
    css = Path(args.css).read_text(encoding="utf-8")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.list_editions:
        html_out = build_editions_index(editions_from_dir(args.list_editions), css, args.podcast)
    elif args.editions:
        editions = json.loads(Path(args.editions).read_text(encoding="utf-8"))
        html_out = build_editions_index(editions, css, args.podcast)
    else:
        if not args.json:
            raise SystemExit("need --json, --list-editions or --editions")
        ed = json.loads(Path(args.json).read_text(encoding="utf-8"))
        ed["_file"] = Path(args.json).name
        html_out = build_page(ed, css, args.podcast, args.base)
    out.write_text(html_out, encoding="utf-8")
    print("wrote %s (%d chars)" % (out, len(html_out)))


if __name__ == "__main__":
    main()
