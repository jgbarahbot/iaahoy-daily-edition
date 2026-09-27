#!/usr/bin/env python3
"""iaahoy collector — gathers raw candidate material from open-AI sources.

Outputs a JSON "material pack" the curator (the agent) turns into a Spanish
edition. Deterministic + fast; every source is optional (a dead feed degrades
gracefully instead of failing the run).

Sources:
  * Hugging Face trending models + datasets  (public API)
  * Hugging Face daily papers                (public API)
  * Hugging Face blog                        (RSS)
  * GitHub trending repos                    (search API by topic + recency)
  * Web news / subreddits / blogs            (self-hosted SearXNG JSON)

Usage:
    python collector.py --out material.json [--days 2]
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request, ssl
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

UA = "Mozilla/5.0 (X11; Linux x86_64) iaahoy-collector/1.0"
CTX = ssl.create_default_context()

def http_get(url, timeout=25, headers=None, accept=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    if accept:
        h["Accept"] = accept
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", errors="replace")

def jget(url, headers=None, timeout=25):
    return json.loads(http_get(url, timeout=timeout, headers=headers, accept="application/json"))

def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()

# ---- Hugging Face -------------------------------------------------------
def hf_models(limit=15):
    d = jget(f"https://huggingface.co/api/models?sort=trendingScore&limit={limit}")
    out = []
    for m in d:
        out.append({
            "id": m.get("id"),
            "likes": m.get("likes"),
            "downloads": m.get("downloads"),
            "pipeline": m.get("pipeline_tag"),
            "tags": (m.get("tags") or [])[:12],
            "url": f"https://huggingface.co/{m.get('id')}",
        })
    return out

def hf_datasets(limit=10):
    d = jget(f"https://huggingface.co/api/datasets?sort=trendingScore&limit={limit}")
    return [{"id": x.get("id"), "likes": x.get("likes"), "downloads": x.get("downloads"),
             "tags": (x.get("tags") or [])[:12], "url": f"https://huggingface.co/datasets/{x.get('id')}"}
            for x in d]

def hf_papers(limit=10):
    d = jget(f"https://huggingface.co/api/daily_papers?limit={limit}")
    out = []
    for p in d:
        paper = p.get("paper", p)
        title = paper.get("title") or p.get("title")
        arxiv_id = paper.get("id") or p.get("id")
        raw_authors = paper.get("authors") or []
        authors = ", ".join(
            (a.get("name") if isinstance(a, dict) else str(a)) for a in raw_authors[:4]
        )
        out.append({
            "title": title,
            "arxiv_id": arxiv_id,
            "published": (p.get("publishedAt") or "")[:10],
            "authors": authors,
            "summary": strip_tags(paper.get("summary") or p.get("summary") or "")[:240],
            "upvotes": paper.get("upvotes"),
            "hf_url": f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else None,
            "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
        })
    return out

def hf_blog(limit=10):
    xml = http_get("https://huggingface.co/blog/feed.xml", accept="application/rss+xml")
    root = ET.fromstring(xml)
    out = []
    for it in root.iter("item"):
        out.append({
            "title": strip_tags(it.findtext("title")),
            "link": (it.findtext("link") or "").strip(),
            "date": (it.findtext("pubDate") or "").strip(),
            "desc": strip_tags(it.findtext("description"))[:300],
        })
        if len(out) >= limit:
            break
    return out

# ---- GitHub -------------------------------------------------------------
GH_TOPIC_QUERIES = [
    ("llm", "modelos y tooling LLM"),
    ("llm-agent", "agentes"),
    ("llm-inference", "inferencia/kernels"),
    ("fine-tuning", "fine-tuning"),
    ("local-llm", "IA local/self-hosted"),
    ("llm-gui", "interfaces"),
]
def gh_trending(days=2):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    tok = os.environ.get("GITHUB_TOKEN") or ""
    headers = {"Authorization": f"token {tok}"} if tok else {}
    seen = {}
    for q, _ in GH_TOPIC_QUERIES:
        url = (f"https://api.github.com/search/repositories?per_page=8&sort=stars&order=desc"
               f"&q={urllib.parse.quote(q + ' created:' + chr(62) + since)}")
        try:
            d = jget(url, headers=headers, timeout=25)
        except Exception as e:
            continue
        for r in d.get("items", []):
            fn = r["full_name"]
            if fn in seen:
                continue
            seen[fn] = {
                "name": fn,
                "desc": (r.get("description") or "").strip(),
                "stars": f"★ {r['stargazers_count']:,}",
                "lang": r.get("language") or "",
                "pushed": (r.get("pushed_at") or "")[:10],
                "url": r["html_url"],
            }
            if len(seen) >= 24:
                break
        time.sleep(0.3)
    # rank by star count
    return sorted(seen.values(), key=lambda x: int(re.sub(r"[^\d]", "", x["stars"]) or 0), reverse=True)[:20]

# ---- Web via SearXNG ----------------------------------------------------
SEARXNG = "http://127.0.0.1:8080/search"
def searxng(query, categories="general", limit=12, engines=None):
    params = {"q": query, "format": "json", "categories": categories}
    if engines:
        params["engines"] = engines
    url = SEARXNG + "?" + urllib.parse.urlencode(params)
    try:
        d = jget(url, timeout=30)
    except Exception:
        return []
    out = []
    for r in d.get("results", []):
        out.append({
            "title": strip_tags(r.get("title")),
            "url": r.get("url"),
            "content": strip_tags(r.get("content"))[:260],
            "engine": r.get("engine"),
        })
        if len(out) >= limit:
            break
    return out

def web_news():
    packs = []
    queries = [
        ("open source LLM release", "general", "noticias de modelos abiertos"),
        ("local LLM self-hosted news", "general", "IA self-hosted"),
        ("reddit LocalLLaMA top this week", "general", "subreddit LocalLLaMA"),
        ("reddit LocalLLaMA top this week", "chat", "subreddit LocalLLaMA"),
        ("open source AI agents release", "general", "agentes"),
        ("llm inference engine kernel release", "general", "kernels"),
        ("Hugging Face blog open model", "general", "Hugging Face"),
    ]
    for q, cat, label in queries:
        res = searxng(q, cat, limit=10)
        for r in res:
            r["query"] = q
            r["label"] = label
        packs.extend(res)
        time.sleep(0.2)
    # dedupe by URL
    seen, dedup = set(), []
    for r in packs:
        u = r.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        dedup.append(r)
    return dedup[:60]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="material.json")
    ap.add_argument("--days", type=int, default=2)
    args = ap.parse_args()
    material = {"generated_at": datetime.now(timezone.utc).isoformat(), "errors": []}
    for name, fn in [("hf_models", hf_models), ("hf_datasets", hf_datasets),
                     ("hf_papers", hf_papers), ("hf_blog", hf_blog),
                     ("gh_trending", lambda: gh_trending(args.days)), ("web", web_news)]:
        try:
            material[name] = fn()
            print(f"[ok] {name}: {len(material[name])} items", file=sys.stderr)
        except Exception as e:
            material[name] = []
            material["errors"].append(f"{name}: {e}")
            print(f"[fail] {name}: {e}", file=sys.stderr)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(material, f, ensure_ascii=False, indent=2)
    print(f"material pack -> {args.out}")

if __name__ == "__main__":
    main()
