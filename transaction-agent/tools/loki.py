from __future__ import annotations

import os
from typing import Any

import requests


class LokiTool:
    def __init__(self) -> None:
        self.base_url = os.getenv("LOKI_BASE_URL", "https://microservices.socket.tech/loki").rstrip("/")

    def get_transaction(self, tx_hash: str) -> dict[str, Any] | None:
        response = requests.get(
            f"{self.base_url}/tx",
            params={"txHash": tx_hash},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        result = payload.get("result") or []
        if payload.get("success") is True and result:
            return result[0]
        return None

    @staticmethod
    def parse_identifier(identifier: str) -> dict[str, str | None]:
        order_id, from_chain_id, bridge_name, tx_type = (identifier.split("-", 3) + [None] * 4)[:4]
        return {
            "order_id": order_id,
            "from_chain_id": from_chain_id,
            "bridge_name": bridge_name,
            "tx_type": tx_type,
        }

    @staticmethod
    def get_settlement_time(loki_data: dict[str, Any]) -> int | None:
        src_timestamp = loki_data.get("srcBlockTimeStamp")
        dest_timestamp = loki_data.get("destBlockTimeStamp")
        if src_timestamp is None or dest_timestamp is None:
            return None
        return int(dest_timestamp) - int(src_timestamp)
