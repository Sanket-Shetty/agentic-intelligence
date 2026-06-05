from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class MixpanelTool:
    def __init__(self) -> None:
        self.username = os.getenv("MIXPANEL_SERVICE_ACCOUNT_USERNAME", "")
        self.secret = os.getenv("MIXPANEL_SERVICE_ACCOUNT_SECRET", "")
        self.project_id = os.getenv("MIXPANEL_PROJECT_ID", "")
        self.auth = (self.username, self.secret)

    def get_events_for_user(
        self,
        distinct_id: str,
        from_date: str,
        to_date: str,
        event_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            "from_date": from_date,
            "to_date": to_date,
            "project_id": self.project_id,
            "where": f'properties["$distinct_id"] == "{distinct_id}"',
        }
        if event_names:
            params["event"] = json.dumps(event_names)

        response = requests.get(
            "https://data.mixpanel.com/api/2.0/export/",
            params=params,
            auth=self.auth,
            timeout=15,
        )
        response.raise_for_status()

        events: list[dict[str, Any]] = []
        for line in response.text.splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def get_quote_events_around_transaction(
        self,
        user_address: str,
        tx_timestamp: int,
        window_hours: int = 2,
    ) -> list[dict[str, Any]]:
        tx_time = datetime.fromtimestamp(tx_timestamp, tz=timezone.utc)
        from_date = (tx_time - timedelta(hours=window_hours)).date().isoformat()
        to_date = (tx_time + timedelta(hours=window_hours)).date().isoformat()
        events = self.get_events_for_user(user_address, from_date, to_date)
        return sorted(events, key=lambda event: event.get("properties", {}).get("time", 0))

    def get_user_profile(self, distinct_id: str) -> dict[str, Any] | None:
        response = requests.post(
            "https://mixpanel.com/api/query/engage",
            params={"project_id": self.project_id},
            data={"distinct_id": distinct_id},
            auth=self.auth,
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results") or []
        return results[0] if results else None
