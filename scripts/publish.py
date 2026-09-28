#!/usr/bin/env python3
"""iaahoy publisher — renders the site from edition JSONs and pushes to
GitHub Pages, flattening history each day so NO old podcasts are kept.

Site layout (repo = <owner>/<site-repo>, a GitHub *project* site):
    index.html                  -> latest edition
    editions/<YYYY-MM-DD>.html  -> dated permalink per edition
    editions/index.html         -> archive (all editions, newest first)
    podcast.mp3                 -> today's audio (single slot, overwritten daily)

The edition JSONs (editions/<date>.json) are the single source of truth:
this script renders them with render.py, so there are no stale pre-rendered
HTML files to drift out of sync.

Flow:  assemble() -> build/site   |  clone to git/   |  sync build/site -> git/
       |  flatten (drop history -> single root commit)  |  force-push.

A safety guard refuses to push if the tree would be empty (e.g. a render
failure), so a bad run can never wipe the live site.

PARAMETERIZATION — no GitHub identity is hardcoded in this script. Everything
is a parameter, resolved in this precedence (CLI > env > derived):
    --user / IAAHOY_GH_USER     GitHub username (for auth + commit author).
                                 Defaults to the token's own login, derived
                                 from the GitHub API, so no config is needed.
    --token-env                 Name of the env var holding the push token
                                 (default: GITHUB_IAAHOY_TOKEN).
    --repo / IAAHOY_SITE_REPO   Remote URL to push to
                                 (default: https://github.com/<user>/iaahoy.git).
    --site-url / IAAHOY_SITE_URL  Optional Pages URL for the final report
                                 (default: derived from the repo).
    IAAHOY_GIT                  clone dir (default <project>/git).

Usage:
    python publish.py            # render + assemble + flatten + force-push
    python publish.py --no-push  # render + assemble + local orphan commit only
    python publish.py --dry-run  # assemble only; no git at all
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

PROJ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
EDITIONS_DIR = os.path.join(PROJ, "editions")
BUILD = os.path.join(PROJ, "build", "site")
GIT = os.environ.get("IAAHOY_GIT", os.path.join(PROJ, "git"))
RENDER = os.path.join(PROJ, "scripts", "render.py")
CSS = os.path.join(PROJ, "templates", "style.css")
PODCAST_SRC = os.path.join(PROJ, "build", "podcast.mp3")
DATE_JSON_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")
ENV_PATH = os.path.expanduser("~/.hermes/.env")


def _env_var(name):
    """Read one variable from ~/.hermes/.env (first occurrence)."""
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get(name, "")


def resolve_token(token_env):
    return os.environ.get(token_env, "") or _env_var(token_env)


def derive_user_from_token(token):
    """GitHub username owning `token`, via the /user API ('' if unavailable)."""
    if not token:
        return ""
    try:
        req = urllib.request.Request("https://api.github.com/user",
                                     headers={"Authorization": "Bearer " + token,
                                              "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp).get("login", "") or ""
    except Exception:
        return ""


def resolve_user(cli_user, token):
    """CLI > IAAHOY_GH_USER (env file or environ) > token's login (derived)."""
    return cli_user or os.environ.get("IAAHOY_GH_USER") \
        or _env_var("IAAHOY_GH_USER") or derive_user_from_token(token)


def resolve_repo(cli_repo, user):
    """CLI > IAAHOY_SITE_REPO (env file or environ) > https://github.com/<user>/iaahoy.git."""
    return cli_repo or os.environ.get("IAAHOY_SITE_REPO") \
        or _env_var("IAAHOY_SITE_REPO") or "https://github.com/%s/iaahoy.git" % user


def resolve_site_url(cli_url, repo):
    """Pages URL: CLI > IAAHOY_SITE_URL > derived from repo <owner>/<name>."""
    if cli_url:
        return cli_url
    env_url = os.environ.get("IAAHOY_SITE_URL") or _env_var("IAAHOY_SITE_URL")
    if env_url:
        return env_url
    tail = repo.split("github.com/", 1)[-1].strip("/").removesuffix(".git")
    owner, _, name = tail.rpartition("/")
    if not owner or not name:
        return ""
    return "https://%s.github.io/%s/" % (owner, name)


def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def _git_ok():
    """True if GIT is a usable clone (a git repo whose HEAD resolves)."""
    if not os.path.exists(os.path.join(GIT, ".git")):
        return False
    r = run(["git", "-C", GIT, "rev-parse", "--abbrev-ref", "HEAD"])
    return r.returncode == 0 and r.stdout.strip() not in ("", "HEAD")


def collect_editions():
    """Return edition dicts sorted newest-first, from editions/*.json."""
    out = []
    for fn in os.listdir(EDITIONS_DIR):
        m = DATE_JSON_RE.match(fn)
        if not m:
            continue
        date = m.group(1)
        jf = os.path.join(EDITIONS_DIR, fn)
        try:
            e = json.load(open(jf, encoding="utf-8"))
        except Exception:
            continue
        out.append({
            "date": date,
            "json": jf,
            "edition": e.get("edition", "Edición"),
            "weekday": e.get("weekday_long", ""),
            "date_label": e.get("date", date),
        })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def _render(args):
    r = run([sys.executable, RENDER] + args)
    if r.returncode != 0:
        print("RENDER FAILED:\n" + (r.stderr or r.stdout))
        sys.exit(1)


def assemble():
    """Render every edition from JSONs into build/site and copy the podcast."""
    eds = collect_editions()
    if not eds:
        print("ERROR: no edition JSONs in", EDITIONS_DIR)
        sys.exit(1)
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(os.path.join(BUILD, "editions"), exist_ok=True)

    # latest -> index.html (podcast at site root)
    _render(["--json", eds[0]["json"], "--css", CSS,
             "--podcast", "podcast.mp3", "--out", os.path.join(BUILD, "index.html")])
    # archive list (one level deep -> podcast one level up)
    _render(["--list-editions", EDITIONS_DIR, "--css", CSS,
             "--podcast", "../podcast.mp3", "--out", os.path.join(BUILD, "editions", "index.html")])
    # dated permalinks (podcast one level up)
    for e in eds:
        _render(["--json", e["json"], "--css", CSS,
                 "--podcast", "../podcast.mp3",
                 "--out", os.path.join(BUILD, "editions", e["date"] + ".html")])

    # copy today's audio into the build (single slot, overwritten daily)
    if os.path.exists(PODCAST_SRC):
        shutil.copyfile(PODCAST_SRC, os.path.join(BUILD, "podcast.mp3"))
        print(f"podcast copied ({os.path.getsize(PODCAST_SRC)} bytes)")
    else:
        print("WARNING:", PODCAST_SRC, "not found — publishing WITHOUT audio")
    print(f"assembled {len(eds)} edition(s); latest {eds[0]['date']}")
    return eds


def sync_into_git():
    """Copy build/site into the git working tree (repo holds ONLY the site).
    Delete any top-level entry that is not .git and not in the current build,
    nuke + recopy editions/, then copy the build in. Never recurses into .git."""
    os.makedirs(GIT, exist_ok=True)
    build_top = set(os.listdir(BUILD))
    for entry in os.listdir(GIT):
        if entry == ".git" or entry in build_top:
            continue
        p = os.path.join(GIT, entry)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    old_ed = os.path.join(GIT, "editions")
    if os.path.isdir(old_ed):
        shutil.rmtree(old_ed)
    for root, dirs, files in os.walk(BUILD):
        rel = os.path.relpath(root, BUILD)
        dest = os.path.join(GIT, rel) if rel != "." else GIT
        os.makedirs(dest, exist_ok=True)
        for fn in files:
            shutil.copyfile(os.path.join(root, fn), os.path.join(dest, fn))


def _flatten_commit(user, latest_date):
    """Drop history and commit the current working tree as a single root
    commit on 'main'. Returns 0 on success, 1 if the tree is unsafe (empty).
    The live site is only touched later, on force-push — and only if this
    returns 0 with a non-empty tree that contains index.html."""
    run(["git", "-C", GIT, "config", "user.name", user])
    run(["git", "-C", GIT, "config", "user.email", user + "@users.noreply.github.com"])
    # stage the tree, then drop history so main becomes unborn
    run(["git", "-C", GIT, "add", "-A"])
    run(["git", "-C", GIT, "update-ref", "-d", "refs/heads/main"])
    run(["git", "-C", GIT, "add", "-A"])
    st = run(["git", "-C", GIT, "status", "--porcelain"]).stdout.strip()
    tree = run(["git", "-C", GIT, "ls-files"]).stdout
    if not st or "index.html" not in tree:
        print("FATAL: empty tree or missing index.html — NOT pushing (live site preserved)")
        run(["git", "-C", GIT, "checkout", "-f", "main"])
        return 1
    c = run(["git", "-C", GIT, "commit", "-q", "-m", f"iaahoy: {latest_date}"])
    if c.returncode != 0:
        print("commit failed:\n" + c.stderr)
        return 1
    return 0


def _auth_url(repo, user, token):
    """Build the authenticated clone/push URL.

    Fine-grained PATs (github_pat_) REQUIRE the owning username as the git
    user; the legacy 'x-access-token' username is rejected with 403 for those.
    Classic PATs work with either, so keep 'x-access-token' as the fallback
    only when no username is known."""
    auth_user = user or "x-access-token"
    return repo.replace("https://", "https://" + auth_user + ":" + token + "@")


def git_flatten_push(no_push, user, token, repo, site_url):
    if not token:
        print("ERROR: push token not found (set the token env var or pass --token-env)")
        return 1
    if not user:
        print("ERROR: could not determine the GitHub username "
              "(pass --user, set IAAHOY_GH_USER, or use a token whose login is resolvable)")
        return 1
    auth_url = _auth_url(repo, user, token)
    # self-heal: re-clone if git/ is missing or corrupted
    if os.path.isdir(GIT) and not _git_ok():
        print("git/ present but broken — re-cloning")
        shutil.rmtree(GIT, ignore_errors=True)
    if not _git_ok():
        r = run(["git", "clone", auth_url, GIT])
        if r.returncode != 0:
            print("clone failed; initializing fresh repo (first push)")
            return _fresh(auth_url, user, no_push)
    sync_into_git()
    latest = collect_editions()[0]["date"]
    if _flatten_commit(user, latest) != 0:
        return 1
    if no_push:
        print("[no-push] single root commit made locally; not pushed")
        return 0
    r = run(["git", "-C", GIT, "push", "--force", "-u", "origin", "main"])
    if r.returncode != 0:
        print("PUSH FAILED:\n" + r.stderr)
        return 1
    print(f"flattened + force-pushed {repo} main (single commit for {latest})")
    if site_url:
        print(f"site: {site_url}")
    return 0


def _fresh(auth_url, user, no_push):
    os.makedirs(GIT, exist_ok=True)
    run(["git", "-C", GIT, "init", "-b", "main"])
    sync_into_git()
    run(["git", "-C", GIT, "config", "user.name", user])
    run(["git", "-C", GIT, "config", "user.email", user + "@users.noreply.github.com"])
    run(["git", "-C", GIT, "add", "-A"])
    st = run(["git", "-C", GIT, "status", "--porcelain"]).stdout.strip()
    if not st or "index.html" not in run(["git", "-C", GIT, "ls-files"]).stdout:
        print("FATAL: empty tree — NOT pushing")
        return 1
    run(["git", "-C", GIT, "commit", "-q", "-m", "iaahoy: initial site"])
    if no_push:
        print("[no-push] committed only")
        return 0
    run(["git", "-C", GIT, "remote", "add", "origin", auth_url])
    r = run(["git", "-C", GIT, "push", "-u", "origin", "main"])
    if r.returncode != 0:
        print("PUSH FAILED:\n" + r.stderr)
        return 1
    print("pushed initial site to origin/main")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--user", default="",
                    help="GitHub username (default: token's login, else IAAHOY_GH_USER)")
    ap.add_argument("--token-env", default="GITHUB_IAAHOY_TOKEN",
                    help="name of the env var holding the push token")
    ap.add_argument("--repo", default="",
                    help="remote URL (default: IAAHOY_SITE_REPO, else <user>/iaahoy.git)")
    ap.add_argument("--site-url", default="",
                    help="Pages URL for the final report (default: derived from repo)")
    args = ap.parse_args()
    token = resolve_token(args.token_env)
    user = resolve_user(args.user, token)
    repo = resolve_repo(args.repo, user)
    site_url = resolve_site_url(args.site_url, repo)
    print(f"publish: user={user} repo={repo} site={site_url or '(unknown)'}")
    if not args.dry_run and not token:
        print(f"NOTE: no token for '{args.token_env}' — the push step will fail")
    assemble()
    if args.dry_run:
        print("[dry-run] no git")
        return 0
    sys.exit(git_flatten_push(args.no_push, user, token, repo, site_url))


if __name__ == "__main__":
    main()
