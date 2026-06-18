from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


SENTRY_TRIAGE_SYSTEM_PROMPT = """
You are a senior production bug triage agent for this Socket/Bungee transaction intelligence repo.

Given a Sentry issue and recent events:
1. Decide whether this looks like a true actionable product/code bug.
2. Identify the most likely failing subsystem and impacted files when possible.
3. Produce a concise reproduction hypothesis.
4. Produce a safe fix plan suitable for Codex to implement in a branch.
5. Produce a GitHub PR body that tags the configured reviewer and links the Sentry issue.

Be conservative. If evidence is insufficient, say it is not confirmed and ask for logs,
environment, or reproduction data instead of inventing a fix.

Return only JSON with:
{
  "confirmed_bug": true | false,
  "confidence": 0.0,
  "severity": "low" | "medium" | "high",
  "likely_area": "short subsystem name",
  "why": "specific evidence-based explanation",
  "reproduction_hypothesis": "short hypothesis",
  "fix_plan": ["step"],
  "test_plan": ["step"],
  "codex_prompt": "ready-to-run prompt for a coding agent",
  "pr_title": "title",
  "pr_body": "body"
}
"""


def summarize_sentry_issue(issue: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing.")

    compact_issue = {
        "id": issue.get("id"),
        "shortId": issue.get("shortId"),
        "title": issue.get("title"),
        "culprit": issue.get("culprit"),
        "permalink": issue.get("permalink"),
        "level": issue.get("level"),
        "count": issue.get("count"),
        "userCount": issue.get("userCount"),
        "firstSeen": issue.get("firstSeen"),
        "lastSeen": issue.get("lastSeen"),
        "metadata": issue.get("metadata"),
        "project": issue.get("project"),
    }
    compact_events = [_compact_event(event) for event in events[:5]]

    response = OpenAI().chat.completions.create(
        model=os.getenv("SENTRY_TRIAGE_MODEL", "gpt-4.1-mini"),
        messages=[
            {"role": "system", "content": SENTRY_TRIAGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"issue": compact_issue, "events": compact_events},
                    default=str,
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    payload = json.loads(content)
    payload.setdefault("confirmed_bug", False)
    payload.setdefault("confidence", 0)
    payload.setdefault("severity", "medium")
    payload.setdefault("fix_plan", [])
    payload.setdefault("test_plan", [])
    return payload


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    entries = event.get("entries") or []
    exception_entries = [entry for entry in entries if entry.get("type") in {"exception", "stacktrace", "message"}]
    return {
        "eventID": event.get("eventID"),
        "dateCreated": event.get("dateCreated"),
        "title": event.get("title"),
        "message": event.get("message"),
        "platform": event.get("platform"),
        "environment": event.get("environment"),
        "release": event.get("release"),
        "tags": event.get("tags"),
        "contexts": event.get("contexts"),
        "entries": exception_entries[:3],
    }

