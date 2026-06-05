from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

from agent.prompts import SQL_ANALYST_SYSTEM_PROMPT
from tools.loki import LokiTool
from tools.metabase import MetabaseQueryError, MetabaseTool
from tools.mixpanel import MixpanelTool
from utils.parsers import chain_id_to_name, human_readable_amount, slippage_bps

load_dotenv()

app = FastAPI(title="Transaction Intelligence Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IntelligenceRequest(BaseModel):
    value: str = Field(min_length=1)
    input_type: Literal["tx_hash", "request_hash", "auto"] = "auto"
    include_mixpanel: bool = True
    window_hours: int = Field(default=2, ge=1, le=48)


class InsightQueryRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    model: str = "gpt-4.1-mini"


class SourceStatus(BaseModel):
    ok: bool
    error: str | None = None
    found: bool | None = None


def _unix_from_created_at(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return int(datetime.fromisoformat(normalized).timestamp())
        except ValueError:
            return None
    return None


def _safe_call(fn, *args, **kwargs) -> tuple[Any, SourceStatus]:
    try:
        return fn(*args, **kwargs), SourceStatus(ok=True)
    except Exception as exc:
        return None, SourceStatus(ok=False, error=str(exc))


def _quote_count(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if "quote" in str(event.get("event", "")).lower())


def _build_summary(
    postgres_data: dict[str, Any] | None,
    loki_data: dict[str, Any] | None,
    quotes: list[dict[str, Any]],
    mixpanel_events: list[dict[str, Any]],
    anomalies: list[str],
    slippage: dict[str, Any] | None,
) -> str:
    bridge = (loki_data or {}).get("bridgeName") or (postgres_data or {}).get("bridge_name")
    from_chain_id = (loki_data or {}).get("fromChainId") or (postgres_data or {}).get("from_chain_id")
    to_chain_id = (loki_data or {}).get("toChainId") or (postgres_data or {}).get("to_chain_id")
    status = (postgres_data or {}).get("status") or (loki_data or {}).get("destTxStatus")

    parts = [
        f"Status: {status or 'unknown'}",
        f"Bridge: {bridge or 'unknown'}",
    ]

    if from_chain_id and to_chain_id:
        parts.append(f"Route: {chain_id_to_name(int(from_chain_id))} to {chain_id_to_name(int(to_chain_id))}")
    if slippage:
        parts.append(f"Slippage: {slippage['slippage_bps']} bps")
    parts.append(f"Quotes found: {len(quotes)}")
    parts.append(f"Mixpanel events found: {len(mixpanel_events)}")
    parts.append(f"Anomalies: {len(anomalies)}")
    return " | ".join(parts)


def _validate_read_only_sql(sql: str) -> str:
    cleaned = sql.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()

    normalized = re.sub(r"/\*.*?\*/", " ", cleaned, flags=re.DOTALL)
    normalized = re.sub(r"--.*?$", " ", normalized, flags=re.MULTILINE)
    lowered = normalized.lower()

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise HTTPException(status_code=400, detail="Generated SQL must start with SELECT or WITH.")
    if ";" in normalized:
        raise HTTPException(status_code=400, detail="Generated SQL must contain exactly one statement.")

    forbidden = {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "truncate",
        "grant",
        "revoke",
        "copy",
        "call",
        "do",
        "execute",
    }
    found = [word for word in forbidden if re.search(rf"\b{word}\b", lowered)]
    if found:
        raise HTTPException(status_code=400, detail=f"Generated SQL contains forbidden keyword: {found[0]}.")

    return cleaned


def _generate_insight_sql(prompt: str, model: str) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is missing. Add it to transaction-agent/.env to enable natural-language SQL insights.",
        )

    response = OpenAI().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SQL_ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {exc}") from exc

    sql = payload.get("sql")
    if not isinstance(sql, str) or not sql.strip():
        raise HTTPException(status_code=502, detail="LLM did not return a SQL query.")

    payload["sql"] = _validate_read_only_sql(sql)
    payload["chart_type"] = payload.get("chart_type") if payload.get("chart_type") in {"bar", "line", "table", "metric"} else "table"
    payload["title"] = payload.get("title") or "Generated insight"
    payload["explanation"] = payload.get("explanation") or ""
    payload["x_key"] = payload.get("x_key")
    payload["y_key"] = payload.get("y_key")
    return payload


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/pending-transactions")
def pending_transactions() -> dict[str, Any]:
    transactions = MetabaseTool().get_pending_transactions()
    return {"count": len(transactions), "transactions": transactions}


@app.post("/api/query-insights")
def query_insights(request: InsightQueryRequest) -> dict[str, Any]:
    generated = _generate_insight_sql(request.prompt, request.model)
    try:
        rows = MetabaseTool().query(generated["sql"])
    except MetabaseQueryError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Generated SQL was rejected by Metabase.",
                "error": str(exc),
                "sql": generated["sql"],
            },
        ) from exc
    return {
        "prompt": request.prompt,
        "title": generated["title"],
        "sql": generated["sql"],
        "chart_type": generated["chart_type"],
        "x_key": generated["x_key"],
        "y_key": generated["y_key"],
        "explanation": generated["explanation"],
        "row_count": len(rows),
        "rows": rows,
    }


@app.post("/api/intelligence")
def transaction_intelligence(request: IntelligenceRequest) -> dict[str, Any]:
    metabase = MetabaseTool()
    loki = LokiTool()
    mixpanel = MixpanelTool()

    value = request.value.strip()
    is_auto = request.input_type == "auto"
    is_tx_hash = request.input_type == "tx_hash"

    source_status: dict[str, SourceStatus] = {}
    postgres_data: dict[str, Any] | None = None
    loki_data: dict[str, Any] | None = None
    quotes: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        if is_auto:
            futures["metabase_request"] = executor.submit(_safe_call, metabase.get_transaction_by_request_hash, value)
            futures["metabase_transaction"] = executor.submit(_safe_call, metabase.get_transaction_by_hash, value)
            futures["loki"] = executor.submit(_safe_call, loki.get_transaction, value)
        elif is_tx_hash:
            futures["metabase_transaction"] = executor.submit(_safe_call, metabase.get_transaction_by_hash, value)
            futures["loki"] = executor.submit(_safe_call, loki.get_transaction, value)
        else:
            futures["metabase_request"] = executor.submit(_safe_call, metabase.get_transaction_by_request_hash, value)

        for name, future in futures.items():
            data, status = future.result()
            if name == "metabase_request":
                status.found = bool(data)
                source_status[name] = status
                postgres_data = data or postgres_data
            elif name == "metabase_transaction":
                status.found = bool(data)
                source_status[name] = status
                postgres_data = postgres_data or data
            elif name == "loki":
                status.found = bool(data)
                source_status[name] = status
                loki_data = data
            elif name == "quotes":
                status.found = bool(data)
                source_status[name] = status
                quotes = data or []

    order_id = None
    quote_lookup_id = None
    if postgres_data:
        order_id = postgres_data.get("order_id")
        quote_lookup_id = postgres_data.get("quote_id") or postgres_data.get("order_id")
    if not order_id and loki_data and loki_data.get("identifier"):
        order_id = loki.parse_identifier(loki_data["identifier"]).get("order_id")
    if not order_id and not is_tx_hash:
        order_id = value
    if quote_lookup_id and not quotes:
        quotes, source_status["metabase_quotes"] = _safe_call(metabase.get_quotes_for_order, str(quote_lookup_id))
        source_status["metabase_quotes"].found = bool(quotes)
        quotes = quotes or []

    tx_timestamp = None
    user_address = None
    if loki_data:
        tx_timestamp = loki_data.get("srcBlockTimeStamp")
        user_address = loki_data.get("sender")
    if postgres_data:
        tx_timestamp = tx_timestamp or _unix_from_created_at(postgres_data.get("created_at"))
        user_address = user_address or postgres_data.get("user_address")
    if quotes and not user_address:
        user_address = quotes[0].get("user_address")

    mixpanel_events: list[dict[str, Any]] = []
    mixpanel_profile = None
    if request.include_mixpanel and user_address and tx_timestamp:
        mixpanel_events, source_status["mixpanel_events"] = _safe_call(
            mixpanel.get_quote_events_around_transaction,
            user_address,
            int(tx_timestamp),
            request.window_hours,
        )
        mixpanel_events = mixpanel_events or []
        mixpanel_profile, source_status["mixpanel_profile"] = _safe_call(mixpanel.get_user_profile, user_address)

    settlement_time = loki.get_settlement_time(loki_data) if loki_data else None
    slippage = None
    if loki_data and quotes:
        latest_quote = quotes[0]
        quoted_output = latest_quote.get("quoted_output")
        dest_amount = loki_data.get("destAmount")
        decimals = loki_data.get("destTokenDecimals")
        if quoted_output is not None and dest_amount is not None and decimals is not None:
            actual_output = human_readable_amount(str(dest_amount), int(decimals))
            slippage = {
                "quoted_output": float(quoted_output),
                "actual_output": actual_output,
                "token_symbol": loki_data.get("destTokenSymbol"),
                "slippage_bps": slippage_bps(float(quoted_output), actual_output),
            }

    anomalies: list[str] = []
    if postgres_data and loki_data:
        pg_status = str(postgres_data.get("status", "")).lower()
        loki_status = str(loki_data.get("destTxStatus", "")).lower()
        if pg_status and loki_status and pg_status not in loki_status and loki_status not in pg_status:
            anomalies.append(f"Postgres status '{postgres_data.get('status')}' differs from Loki destination status '{loki_data.get('destTxStatus')}'.")
    if loki_data and loki_data.get("destTxStatus") and str(loki_data["destTxStatus"]).upper() != "COMPLETED":
        anomalies.append(f"Destination transaction status is {loki_data['destTxStatus']}.")
    if loki_data and loki_data.get("isPartialTx"):
        anomalies.append("Loki marks this as a partial transaction.")
    if settlement_time is not None and settlement_time > 300:
        anomalies.append(f"Settlement time is unusually long at {settlement_time} seconds.")
    if slippage and slippage["slippage_bps"] < -50:
        anomalies.append(f"High negative slippage detected: {slippage['slippage_bps']} bps.")

    if not any([postgres_data, loki_data, quotes]):
        raise HTTPException(status_code=404, detail="No transaction intelligence data found from Metabase or Loki.")

    return {
        "input": value,
        "input_type": "tx_hash" if is_tx_hash else "request_hash",
        "order_id": order_id,
        "tx_hash": value if is_tx_hash else (postgres_data or {}).get("tx_hash"),
        "user_address": user_address,
        "postgres_data": postgres_data,
        "loki_data": loki_data,
        "quotes": quotes,
        "mixpanel": {
            "events": mixpanel_events,
            "profile": mixpanel_profile,
            "quote_event_count": _quote_count(mixpanel_events),
        },
        "metrics": {
            "settlement_time_seconds": settlement_time,
            "slippage": slippage,
        },
        "anomalies": anomalies,
        "source_status": {key: value.model_dump() for key, value in source_status.items()},
        "summary": _build_summary(postgres_data, loki_data, quotes, mixpanel_events, anomalies, slippage),
    }
