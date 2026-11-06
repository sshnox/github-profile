"""Render a compact card from public GitHub account data."""

import json
import os
from html import escape
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API = "https://api.github.com"


def fetch(path, **params):
    query = "?" + urlencode(params) if params else ""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-stats",
    }
    if token := os.getenv("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API}{path}{query}", headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def account_stats(login):
    user_path = "/users/" + quote(login, safe="")
    user = fetch(user_path)
    stars = 0
    page = 1
    while True:
        repos = fetch(f"{user_path}/repos", type="owner", per_page=100, page=page, sort="full_name")
        stars += sum(repo["stargazers_count"] for repo in repos if not repo["fork"] and not repo["private"])
        if len(repos) < 100:
            break
        page += 1

    merged = fetch("/search/issues", q=f"author:{login} is:pr is:public is:merged -user:{login}", per_page=1)
    if merged["incomplete_results"]:
        raise RuntimeError("GitHub returned incomplete pull request search results")

    return (
        ("Public repos", user["public_repos"]),
        ("Followers", user["followers"]),
        ("Stars earned", stars),
        ("Upstream merges", merged["total_count"]),
    )


def render(stats):
    summary = escape(", ".join(f"{name}: {value:,}" for name, value in stats))
    cells = []
    for i, (name, value) in enumerate(stats):
        x = 27 + i * 188
        cells.append(f'''
    <rect x="{x}" y="68" width="174" height="81" rx="8" fill="#1a2b25" stroke="#3b5549"/>
    <text x="{x+14}" y="105" fill="#c9f58c" font-family="Georgia,serif" font-size="32">{value:,}</text>
    <text x="{x+14}" y="130" fill="#e2ede5" font-family="monospace" font-size="12">{escape(name)}</text>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="194" viewBox="0 0 800 194" role="img" aria-labelledby="title description">
  <title id="title">Public GitHub stats</title>
  <desc id="description">{summary}</desc>
  <rect x="1" y="1" width="798" height="192" rx="13" fill="#101b1b" stroke="#3a544a" stroke-width="2"/>
  <path d="M27 52h746m-746 111h746" stroke="#3a544a"/>
  <circle cx="32" cy="33" r="4" fill="#c9f58c"/>
  <text x="45" y="38" fill="#edf3e8" font-family="monospace" font-size="16" letter-spacing="2">GITHUB STATS</text>
  <text x="773" y="38" text-anchor="end" fill="#afc0b7" font-family="monospace" font-size="11" letter-spacing="1">PUBLIC ACTIVITY</text>
  {''.join(cells)}
  <text x="27" y="182" fill="#afc0b7" font-family="monospace" font-size="10">STARS EXCLUDE FORKS · MERGES EXCLUDE PERSONAL REPOS</text>
</svg>
'''


if __name__ == "__main__":
    login = os.environ["GITHUB_REPOSITORY_OWNER"]
    output = Path("dist/github-stats.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(account_stats(login)), encoding="utf-8")
