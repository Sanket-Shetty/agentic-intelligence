from __future__ import annotations

import os
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class SentryConfigError(RuntimeError):
    pass


class SentryTool:
    def __init__(self) -> None:
        self.base_url = os.getenv("SENTRY_BASE_URL", "https://sentry.io").rstrip("/")
        self.auth_token = os.getenv("SENTRY_AUTH_TOKEN", "")
        self.organization = os.getenv("SENTRY_ORG", "")
        self.project = os.getenv("SENTRY_PROJECT", "")

    def _headers(self) -> dict[str, str]:
        if not self.auth_token:
            raise SentryConfigError("SENTRY_AUTH_TOKEN is missing.")
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

    def _require_org(self) -> str:
        if not self.organization:
            raise SentryConfigError("SENTRY_ORG is missing.")
        return self.organization

    def _require_project(self) -> str:
        if not self.project:
            raise SentryConfigError("SENTRY_PROJECT is missing.")
        return self.project

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def list_issues(self, query: str = "is:unresolved", limit: int = 10) -> list[dict[str, Any]]:
        org = self._require_org()
        project = self._require_project()
        response = requests.get(
            f"{self.base_url}/api/0/projects/{org}/{project}/issues/",
            headers=self._headers(),
            params={"query": query, "statsPeriod": "24h", "limit": limit},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def get_issue(self, issue_id: str) -> dict[str, Any]:
        org = self._require_org()
        response = requests.get(
            f"{self.base_url}/api/0/organizations/{org}/issues/{issue_id}/",
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def get_issue_events(self, issue_id: str, limit: int = 5) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/api/0/issues/{issue_id}/events/",
            headers=self._headers(),
            params={"limit": limit},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def resolve_issue(self, issue_id: str) -> dict[str, Any]:
        org = self._require_org()
        response = requests.put(
            f"{self.base_url}/api/0/organizations/{org}/issues/{issue_id}/",
            headers=self._headers(),
            json={"status": "resolved"},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

