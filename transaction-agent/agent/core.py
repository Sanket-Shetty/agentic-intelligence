from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agent.prompts import SYSTEM_PROMPT
from agent.tools_schema import TOOLS_SCHEMA
from tools.loki import LokiTool
from tools.metabase import MetabaseTool
from tools.mixpanel import MixpanelTool
from utils.parsers import human_readable_amount, slippage_bps


class TransactionIntelligenceAgent:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.client = OpenAI()
        self.model = model
        self.metabase = MetabaseTool()
        self.loki = LokiTool()
        self.mixpanel = MixpanelTool()

    def run(self, user_input: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Build a unified transaction intelligence report for this "
                    f"transaction hash or user address: {user_input}"
                ),
            },
        ]

        for _ in range(8):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                return message.content or ""

            for tool_call in message.tool_calls:
                result = self._dispatch_tool_call(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments or "{}"),
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(result, default=str),
                    }
                )

        final_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                *messages,
                {
                    "role": "user",
                    "content": "Finish with the best report possible using the data already gathered.",
                },
            ],
        )
        return final_response.choices[0].message.content or ""

    def _dispatch_tool_call(self, name: str, arguments: dict[str, Any]) -> Any:
        dispatch = {
            "query_metabase_transaction": self._query_metabase_transaction,
            "get_loki_transaction": self._get_loki_transaction,
            "get_mixpanel_events": self._get_mixpanel_events,
            "calculate_slippage": self._calculate_slippage,
            "get_settlement_time": self._get_settlement_time,
        }

        if name not in dispatch:
            return {"error": f"Unknown tool: {name}"}
        return dispatch[name](**arguments)

    def _query_metabase_transaction(
        self,
        tx_hash: str | None = None,
        order_id: str | None = None,
        user_address: str | None = None,
    ) -> dict[str, Any]:
        if tx_hash:
            transaction = self.metabase.get_transaction_by_hash(tx_hash)
            quotes = self.metabase.get_quotes_for_order(transaction["order_id"]) if transaction and transaction.get("order_id") else []
            return {"transaction": transaction, "quotes": quotes}

        if order_id:
            quotes = self.metabase.get_quotes_for_order(order_id)
            return {"transaction": None, "quotes": quotes}

        if user_address:
            sql = (
                "SELECT id, order_id, tx_hash, dest_tx_hash, status, from_chain_id, "
                "to_chain_id, src_amount, dest_amount, fee, bridge_name, user_address, "
                "recipient, created_at, updated_at FROM bungee_request "
                f"WHERE user_address = '{user_address}' ORDER BY created_at DESC LIMIT 10"
            )
            return {"transactions": self.metabase.query(sql), "quotes": []}

        return {"error": "At least one of tx_hash, order_id, or user_address must be provided."}

    def _get_loki_transaction(self, tx_hash: str) -> dict[str, Any]:
        data = self.loki.get_transaction(tx_hash)
        if not data:
            return {"transaction": None}

        identifier = data.get("identifier")
        return {
            "transaction": data,
            "parsed_identifier": self.loki.parse_identifier(identifier) if identifier else None,
            "settlement_time_seconds": self.loki.get_settlement_time(data),
        }

    def _get_mixpanel_events(
        self,
        user_address: str,
        tx_timestamp: int,
        window_hours: int = 2,
    ) -> dict[str, Any]:
        events = self.mixpanel.get_quote_events_around_transaction(
            user_address=user_address,
            tx_timestamp=tx_timestamp,
            window_hours=window_hours,
        )
        profile = self.mixpanel.get_user_profile(user_address)
        return {"events": events, "profile": profile, "event_count": len(events)}

    def _calculate_slippage(
        self,
        quoted_output: float,
        actual_output: float,
        token_decimals: int,
    ) -> dict[str, Any]:
        actual_output_human = human_readable_amount(str(int(actual_output)), token_decimals)
        return {
            "actual_output_human": actual_output_human,
            "slippage_bps": slippage_bps(quoted_output, actual_output_human),
        }

    @staticmethod
    def _get_settlement_time(src_timestamp: int, dest_timestamp: int) -> dict[str, int]:
        return {"settlement_time_seconds": dest_timestamp - src_timestamp}
