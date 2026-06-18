from __future__ import annotations

import os
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class GitHubConfigError(RuntimeError):
    pass


class GitHubTool:
    def __init__(self) -> None:
        self.base_url = os.getenv("GITHUB_API_BASE_URL", "https://api.github.com").rstrip("/")
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.repository = os.getenv("GITHUB_REPOSITORY", "")
        self.default_base = os.getenv("GITHUB_BASE_BRANCH", "main")
        self.reviewer = os.getenv("GITHUB_REVIEWER_HANDLE", "")

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise GitHubConfigError("GITHUB_TOKEN is missing.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _require_repo(self) -> str:
        if not self.repository:
            raise GitHubConfigError("GITHUB_REPOSITORY is missing. Use owner/repo.")
        return self.repository

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def create_pull_request(
        self,
        head_branch: str,
        title: str,
        body: str,
        base_branch: str | None = None,
        draft: bool = False,
    ) -> dict[str, Any]:
        repo = self._require_repo()
        response = requests.post(
            f"{self.base_url}/repos/{repo}/pulls",
            headers=self._headers(),
            json={
                "title": title,
                "head": head_branch,
                "base": base_branch or self.default_base,
                "body": body,
                "draft": draft,
            },
            timeout=20,
        )
        response.raise_for_status()
        pull_request = response.json()
        if self.reviewer:
            self.request_review(pull_request["number"], [self.reviewer])
        return pull_request

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def request_review(self, pull_number: int, reviewers: list[str]) -> dict[str, Any]:
        repo = self._require_repo()
        response = requests.post(
            f"{self.base_url}/repos/{repo}/pulls/{pull_number}/requested_reviewers",
            headers=self._headers(),
            json={"reviewers": reviewers},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

