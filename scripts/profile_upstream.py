"""Update only the reviewed upstream pull-request table in a profile README.

This is deliberately a curated list, rather than an unrestricted public-event
feed. The recorded summaries are approved text, while states and timestamps
come from the official public GitHub pull-request API. Python stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

README_PATH = Path(__file__).resolve().parents[1] / "README.md"
BEGIN = "<!-- BEGIN:PROFILE_UPSTREAM -->"
END = "<!-- END:PROFILE_UPSTREAM -->"


@dataclass(frozen=True)
class TrackedPR:
    repository: str
    number: int
    summary: str


# Add new contributions only after reviewing what will be displayed publicly.
TRACKED = (
    TrackedPR("rossjrw/rossjrw", 4934, "Recover stalled game states"),
    TrackedPR("pydantic/httpx2", 1330, "Retry failed connection-pool closures"),
    TrackedPR("pydantic/httpx2", 1332, "Support an alternative authentication header"),
    TrackedPR("pydantic/logfire", 2803, "Fix Windows CLI file locking"),
)


def load_public_pr(item: TrackedPR, token: str = "") -> dict[str, Any]:
    url = f"https://api.github.com/repos/{item.repository}/pulls/{item.number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "engineering-signal-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("Unexpected API payload")
    return data


def format_day(value: str) -> str:
    if not value:
        raise ValueError("Missing GitHub update timestamp")
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("GitHub timestamp must include a time zone")
    return date.astimezone(timezone.utc).strftime("%d %b %Y")


def render_row(item: TrackedPR, response: dict[str, Any]) -> str:
    actual_repository = ((response.get("base") or {}).get("repo") or {}).get("full_name")
    if actual_repository != item.repository or response.get("number") != item.number:
        raise ValueError(f"Unexpected repository or pull request for {item.repository} #{item.number}")

    if response.get("merged_at"):
        status = "**Merged**"
        event_time = response["merged_at"]
    elif response.get("state") == "open":
        status = "Draft" if response.get("draft") else "Open"
        event_time = response.get("updated_at")
    elif response.get("state") == "closed":
        status = "Closed (not merged)"
        event_time = response.get("updated_at")
    else:
        raise ValueError("Unknown GitHub pull request state")

    # Only human-reviewed labels appear. Never insert remotely supplied PR titles,
    # descriptions, commit messages, or repository metadata into the public README.
    label = item.repository.split("/", 1)[1]
    url = f"https://github.com/{item.repository}/pull/{item.number}"
    return f"| {label} | [{item.summary} (#{item.number})]({url}) | {status} | {format_day(event_time)} |"


def render_table(rows: list[str]) -> str:
    return "\n".join(
        [
            "| Upstream project | Contribution | Status | Date (UTC) |",
            "| :-- | :-- | :-- | :-- |",
            *rows,
        ]
    )


def replace_section(readme: str, new_table: str) -> str:
    if readme.count(BEGIN) != 1 or readme.count(END) != 1:
        raise ValueError("Expected exactly one matching pair of activity markers")
    start = readme.index(BEGIN) + len(BEGIN)
    finish = readme.index(END)
    if start >= finish:
        raise ValueError("Activity markers are out of order")
    return readme[:start] + "\n" + new_table + "\n" + readme[finish:]


def refresh(
    readme_path: Path = README_PATH,
    fetcher: Callable[[TrackedPR, str], dict[str, Any]] = load_public_pr,
    token: str = "",
) -> bool:
    # Complete all reads and validation before writing anything to disk.
    rows = [render_row(item, fetcher(item, token)) for item in TRACKED]
    source = readme_path.read_text(encoding="utf-8")
    updated = replace_section(source, render_table(rows))
    if updated == source:
        return False
    readme_path.write_text(updated, encoding="utf-8", newline="\n")
    return True


if __name__ == "__main__":
    changed = refresh(token=os.environ.get("GITHUB_TOKEN", ""))
    print("Updated reviewed upstream PR statuses." if changed else "Upstream PR statuses unchanged.")
