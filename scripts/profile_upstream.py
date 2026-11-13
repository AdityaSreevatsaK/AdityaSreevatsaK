"""Discover public upstream PRs and refresh the profile's contribution table.

Only PRs authored by the profile owner in repositories owned by other accounts
are displayed. Newly discovered PRs use a neutral numbered label until their
summary has been reviewed; external API titles and descriptions are never
copied into the README. This deliberately avoids exposing unintended text.

The script uses only the Python standard library and writes on success only.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROFILE_LOGIN = "AdityaSreevatsaK"
README_PATH = Path(__file__).resolve().parents[1] / "README.md"
BEGIN = "<!-- BEGIN:PROFILE_UPSTREAM -->"
END = "<!-- END:PROFILE_UPSTREAM -->"
PER_PAGE = 100
MAX_PAGES = 10
MAX_OPEN_SHOWN = 12
MAX_MERGED_SHOWN = 3

# Safe, manually checked summaries. Future PRs are discovered without editing
# this mapping; they appear with a neutral numeric label until curated.
REVIEWED_SUMMARIES = {
    ("pytest-dev/pytest-cov", 775): "Fix coverage merging for custom file tracers",
    ("pydantic/httpx2", 1334): "Fix HTTP/2 response stalls",
    ("pydantic/httpx2", 1333): "Support larger SSE events",
    ("pydantic/logfire", 2803): "Fix Windows log-clean file locking",
    ("pydantic/httpx2", 1332): "Support an alternative authentication header",
    ("pydantic/httpx2", 1330): "Retry failed pool stream closures",
    ("rossjrw/rossjrw", 4934): "Recover stalled game states",
}


class UpstreamUpdateError(ValueError):
    """Prevent incomplete or unexpected API responses from changing the README."""


def query_for(state: str, login: str = PROFILE_LOGIN) -> str:
    if state not in {"open", "merged"}:
        raise ValueError("Unsupported state")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
        raise ValueError("Invalid GitHub login")
    return f"is:pr author:{login} is:{state} is:public -user:{login}"


def search_page(query: str, page: int, token: str = "") -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {"q": query, "per_page": PER_PAGE, "page": page, "sort": "updated", "order": "desc"}
    )
    request = urllib.request.Request(
        f"https://api.github.com/search/issues?{params}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-profile-upstream-contributions",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise UpstreamUpdateError("Unexpected search result type")
    return payload


def search_all(query: str, fetcher: Callable[[str, int, str], dict[str, Any]], token: str = "") -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    total = None
    for page in range(1, MAX_PAGES + 1):
        data = fetcher(query, page, token)
        if not isinstance(data, dict) or data.get("incomplete_results") is not False:
            raise UpstreamUpdateError("GitHub search returned incomplete data")
        if not isinstance(data.get("total_count"), int) or data["total_count"] < 0:
            raise UpstreamUpdateError("Invalid total_count")
        if total is None:
            total = data["total_count"]
            if total > MAX_PAGES * PER_PAGE:
                raise UpstreamUpdateError("Search exceeds safe pagination cap")
        elif total != data["total_count"]:
            raise UpstreamUpdateError("Search results changed during pagination")
        items = data.get("items")
        if not isinstance(items, list):
            raise UpstreamUpdateError("Search results missing items")
        results.extend(items)
        if len(results) >= total:
            return results[:total]
        if not items:
            raise UpstreamUpdateError("Missing page of search results")
    raise UpstreamUpdateError("Search pagination did not finish")


def to_record(item: dict[str, Any], login: str = PROFILE_LOGIN, expected: str = "open") -> dict[str, str] | None:
    if not isinstance(item, dict):
        raise UpstreamUpdateError("Unexpected search item")
    base = item.get("repository_url")
    if not isinstance(base, str) or not base.startswith("https://api.github.com/repos/"):
        raise UpstreamUpdateError("Unexpected repository URL")
    repository = base.removeprefix("https://api.github.com/repos/")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise UpstreamUpdateError("Invalid repository name")
    owner = repository.split("/", 1)[0]
    if owner.casefold() == login.casefold():
        return None
    user = item.get("user") or {}
    if user.get("login", login).casefold() != login.casefold():
        raise UpstreamUpdateError("Search result authored by another account")
    number = item.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise UpstreamUpdateError("Invalid pull request number")
    expected_url = f"https://github.com/{repository}/pull/{number}"
    if item.get("html_url") != expected_url:
        raise UpstreamUpdateError("PR link does not match repository and number")
    metadata = item.get("pull_request") or {}
    if metadata.get("html_url") != expected_url:
        raise UpstreamUpdateError("Missing or inconsistent PR metadata")
    if expected == "open":
        if item.get("state") != "open" or metadata.get("merged_at"):
            raise UpstreamUpdateError("Open search returned non-open PR")
        stamp = item.get("updated_at")
        status = "Draft" if item.get("draft") else "Open"
    elif expected == "merged":
        stamp = metadata.get("merged_at")
        if item.get("state") != "closed" or not stamp:
            raise UpstreamUpdateError("Merged search returned unmerged PR")
        status = "**Merged**"
    else:
        raise UpstreamUpdateError("Unsupported status")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("No timezone")
    except (ValueError, TypeError, AttributeError) as exc:
        raise UpstreamUpdateError("Invalid GitHub timestamp") from exc
    return {
        "repository": repository,
        "number": number,
        "url": expected_url,
        "status": status,
        "updated": parsed.astimezone(timezone.utc).strftime("%d %b %Y"),
        "sort_time": parsed.isoformat(),
    }


def collect(fetcher: Callable[[str, int, str], dict[str, Any]] = search_page,
            token: str = "", login: str = PROFILE_LOGIN) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    groups = []
    for status in ("open", "merged"):
        raw = search_all(query_for(status, login), fetcher, token)
        found: dict[str, dict[str, str]] = {}
        for item in raw:
            record = to_record(item, login, status)
            if record is not None:
                found[record["url"]] = record
        groups.append(sorted(found.values(), key=lambda rec: rec["sort_time"], reverse=True))
    return groups[0], groups[1]


def row(pr: dict[str, str]) -> str:
    repo = pr["repository"]
    number = pr["number"]
    label = REVIEWED_SUMMARIES.get((repo, number), f"Pull request #{number}")
    # The repository/URL are validated. Labels are only trusted local literals.
    return f"| {repo} | [{label} (#{number})]({pr['url']}) | {pr['status']} | {pr['updated']} |"


def render(open_prs: list[dict[str, str]], merged_prs: list[dict[str, str]]) -> str:
    header = (
        f"**Open upstream PRs: {len(open_prs)}** · **Merged: {len(merged_prs)}** · "
        f"[View all upstream PRs](https://github.com/pulls?q=is%3Apr+author%3A{PROFILE_LOGIN}+-user%3A{PROFILE_LOGIN})"
    )
    rows = [
        header,
        "",
        "| Repository | Contribution | Status | Last activity (UTC) |",
        "| :-- | :-- | :-- | :-- |",
        *(row(pr) for pr in open_prs[:MAX_OPEN_SHOWN]),
        *(row(pr) for pr in merged_prs[:MAX_MERGED_SHOWN]),
    ]
    if len(open_prs) > MAX_OPEN_SHOWN:
        rows.append(f"\nShowing the {MAX_OPEN_SHOWN} most recently active open PRs; follow the link above for the full list.")
    return "\n".join(rows)


def replace_section(readme: str, content: str) -> str:
    if readme.count(BEGIN) != 1 or readme.count(END) != 1:
        raise UpstreamUpdateError("Expected one matching pair of section markers")
    start = readme.index(BEGIN) + len(BEGIN)
    end = readme.index(END)
    if end <= start:
        raise UpstreamUpdateError("Section markers are reversed")
    return readme[:start] + "\n" + content + "\n" + readme[end:]


def refresh(path: Path = README_PATH, fetcher: Callable[[str, int, str], dict[str, Any]] = search_page,
            token: str = "") -> bool:
    # Search/validation finish before any file is changed. A failure cannot
    # replace the existing table with partial or invented information.
    opened, merged = collect(fetcher, token)
    source = path.read_text(encoding="utf-8")
    next_source = replace_section(source, render(opened, merged))
    if source == next_source:
        return False
    path.write_text(next_source, encoding="utf-8", newline="\n")
    return True


if __name__ == "__main__":
    changed = refresh(token=os.environ.get("GITHUB_TOKEN", ""))
    print("Refreshed public upstream PR discovery." if changed else "Upstream section unchanged.")