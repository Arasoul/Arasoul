"""Generate self-owned GitHub profile stats SVGs for the profile README.

Renders four SVGs into assets/stats/:
  github-stats-light.svg / github-stats-dark.svg  -> activity snapshot
  languages-light.svg    / languages-dark.svg     -> language mix

Run locally (no token needed for a public profile) or in a GitHub Action
(GITHUB_TOKEN is used when present). No third-party stats service involved.

Language rule: Jupyter Notebook is excluded from the language chart because
notebook JSON artifacts distort an otherwise code-composition signal.
"""

import json
import os
import sys
import urllib.request
from html import escape

OWNER = os.environ.get("PROFILE_OWNER", "Arasoul")
OUT_DIR = os.path.join("assets", "stats")
EXCLUDED_LANGS = {"Jupyter Notebook"}

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


def api(path):
    url = "https://api.github.com" + path
    headers = {
        "User-Agent": "profile-stats-generator",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = api(f"/users/{OWNER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def largest_remainder(items):
    """Round a {label: pct} dict into integer percentages summing to 100."""
    total = sum(items.values()) or 1
    raw, assigned = {}, 0
    for label, value in items.items():
        exact = value * 100.0 / total
        floor = int(exact)
        raw[label] = (floor, exact - floor, exact)
        assigned += floor
    remainder = 100 - assigned
    for label, *_ in sorted(raw.items(), key=lambda kv: -kv[1][1]):
        if remainder <= 0:
            break
        floor, frac, exact = raw[label]
        raw[label] = (floor + 1, frac, exact)
        remainder -= 1
    return {label: entry[0] for label, entry in raw.items()}


def gather():
    repos = fetch_repos()
    public_repos = len(repos)
    stars = sum(r.get("stargazers_count") or 0 for r in repos)
    forks = sum(r.get("forks_count") or 0 for r in repos)

    lang_counts = {}
    for r in repos:
        lang = r.get("language")
        if not lang or lang in EXCLUDED_LANGS:
            continue
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    langs = sorted(lang_counts.items(), key=lambda kv: -kv[1])
    pcts = largest_remainder(dict(langs))
    rows = [((label, count, pcts[label])) for label, count in langs]

    return {
        "public_repos": public_repos,
        "stars": stars,
        "forks": forks,
        "rows": rows,
    }


def render_stats(data, palette):
    c = palette
    card = (
        f'<rect x="2" y="2" width="356" height="206" rx="16" '
        f'fill="{c["bg"]}" stroke="{c["line"]}" stroke-width="1.5"/>'
    )
    tape = (
        f'<rect x="290" y="8" width="48" height="12" rx="3" fill="{c["tape"]}" '
        f'opacity="0.9"/>'
    )
    title = (
        f'<text x="18" y="36" font-family="{c["font"]}" font-size="13" '
        f'letter-spacing="2.5" fill="{c["text"]}">PROFILE&nbsp;STATS</text>'
        f'<text x="342" y="36" text-anchor="end" font-family="{c["font"]}" '
        f'font-size="11" fill="{c["muted"]}">auto&nbsp;refresh&nbsp;·&nbsp;github&nbsp;action</text>'
    )
    divider = (
        f'<path d="M16 51 H344" stroke="{c["dash"]}" stroke-width="1" '
        f'stroke-dasharray="4 4"/>'
    )
    accents = ""
    for x, y in enumerate([75, 180, 285]):
        accents += f'<circle cx="{y}" cy="63" r="2.5" fill="{c["accent"]}"/>'
    nums = data
    blocks = ""
    for x, key, label in [
        (75, "public_repos", "public&nbsp;repos"),
        (180, "stars", "stars"),
        (285, "forks", "forks"),
    ]:
        blocks += (
            f'<text x="{x}" y="118" text-anchor="middle" '
            f'font-family="{c["font"]}" font-size="38" font-weight="700" '
            f'fill="{c["text"]}">{nums[key]}</text>'
            f'<text x="{x}" y="142" text-anchor="middle" '
            f'font-family="{c["font"]}" font-size="11" letter-spacing="1.5" '
            f'fill="{c["muted"]}">{label}</text>'
        )
    footer = (
        f'<path d="M16 160 H344" stroke="{c["dash"]}" stroke-width="1" '
        f'stroke-dasharray="4 4"/>'
        f'<text x="18" y="184" font-family="{c["font"]}" font-size="11" '
        f'fill="{c["muted"]}">generated&nbsp;locally&nbsp;·&nbsp;no&nbsp;third-party&nbsp;service</text>'
        f'<text x="342" y="184" text-anchor="end" font-family="{c["font"]}" '
        f'font-size="11" fill="{c["muted"]}">@Arasoul</text>'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="210" '
        f'viewBox="0 0 360 210" role="img" aria-labelledby="statsTitle">'
        f'<title id="statsTitle">Ahmed\'s GitHub activity statistics</title>'
        f'{card}{tape}{title}{divider}{accents}{blocks}{footer}'
        f"</svg>"
    )
    return svg


def render_langs(rows, palette):
    c = palette
    card = (
        f'<rect x="2" y="2" width="356" height="236" rx="16" '
        f'fill="{c["bg"]}" stroke="{c["line"]}" stroke-width="1.5"/>'
    )
    tape = (
        f'<rect x="290" y="8" width="48" height="12" rx="3" fill="{c["tape"]}" '
        f'opacity="0.9"/>'
    )
    title = (
        f'<text x="18" y="36" font-family="{c["font"]}" font-size="13" '
        f'letter-spacing="2.5" fill="{c["text"]}">REPO&nbsp;LANGUAGES</text>'
        f'<text x="342" y="36" text-anchor="end" font-family="{c["font"]}" '
        f'font-size="11" fill="{c["muted"]}">by&nbsp;primary&nbsp;language</text>'
    )
    divider = (
        f'<path d="M16 51 H344" stroke="{c["dash"]}" stroke-width="1" '
        f'stroke-dasharray="4 4"/>'
    )
    body = ""
    y = 78
    for label, count, pct in rows:
        bar_full = 180
        w = max(2, int(round(bar_full * pct / 100.0)))
        body += (
            f'<text x="18" y="{y}" font-family="{c["font"]}" font-size="13" '
            f'fill="{c["text"]}">{escape(label)}</text>'
            f'<text x="18" y="{y + 14}" font-family="{c["font"]}" font-size="10" '
            f'fill="{c["muted"]}">×{count}</text>'
            f'<rect x="140" y="{y - 8}" width="{bar_full}" height="10" rx="5" '
            f'fill="{c["track"]}"/>'
            f'<rect x="140" y="{y - 8}" width="{w}" height="10" rx="5" '
            f'fill="{c["accent"]}"/>'
            f'<text x="344" y="{y}" text-anchor="end" font-family="{c["font"]}" '
            f'font-size="13" font-weight="700" fill="{c["text"]}">{pct}%</text>'
        )
        y += 30
    footer = (
        f'<path d="M16 218 H344" stroke="{c["dash"]}" stroke-width="1" '
        f'stroke-dasharray="4 4"/>'
        f'<text x="18" y="231" font-family="{c["font"]}" font-size="10" '
        f'fill="{c["muted"]}">no-code&nbsp;repos&nbsp;skipped&nbsp;·&nbsp;jupyter&nbsp;notebook&nbsp;excluded</text>'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="240" '
        f'viewBox="0 0 360 240" role="img" aria-labelledby="langsTitle">'
        f'<title id="langsTitle">Languages used across Ahmed\'s public repositories</title>'
        f'{card}{tape}{title}{divider}{body}{footer}'
        f"</svg>"
    )
    return svg


def main():
    data = gather()
    if not data["rows"]:
        print("no language data found", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)

    palettes = {
        "light": {
            "bg": "#ffffff", "line": "#e2e8f0", "dash": "#cbd5e1",
            "text": "#0f172a", "muted": "#64748b", "accent": "#b45309",
            "track": "#f1f5f9", "tape": "#f59e0b", "font": MONO,
        },
        "dark": {
            "bg": "#1e293b", "line": "#334155", "dash": "#475569",
            "text": "#e2e8f0", "muted": "#94a3b8", "accent": "#f59e0b",
            "track": "#334155", "tape": "#f59e0b", "font": MONO,
        },
    }

    files = {
        "github-stats-light.svg": render_stats(data, palettes["light"]),
        "github-stats-dark.svg": render_stats(data, palettes["dark"]),
        "languages-light.svg": render_langs(data["rows"], palettes["light"]),
        "languages-dark.svg": render_langs(data["rows"], palettes["dark"]),
    }

    for name, content in files.items():
        content = content.replace("&nbsp;", "&#160;")
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"wrote {path} ({len(content)} bytes)")

    print(
        f"data: repos={data['public_repos']} stars={data['stars']} "
        f"forks={data['forks']} langs={[(l, c) for l, c, _ in data['rows']]}"
    )


if __name__ == "__main__":
    main()