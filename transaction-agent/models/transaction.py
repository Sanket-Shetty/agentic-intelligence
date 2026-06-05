from __future__ import annotations

from pydantic import BaseModel, Field


class QuoteData(BaseModel):
    quote_request_id: str | None = None
    quoted_at: str | None = None
    bridge_name: str | None = None
    quoted_output: float | None = None
    quoted_fee: float | None = None
    route: str | None = None
    estimated_time: int | None = None


class LokiData(BaseModel):
    bridge_name: str | None = None
    src_tx_hash: str | None = None
    dest_tx_hash: str | None = None
    src_amount_raw: str | None = None
    dest_amount_raw: str | None = None
    src_token_symbol: str | None = None
    dest_token_symbol: str | None = None
    src_token_decimals: int | None = None
    dest_token_decimals: int | None = None
    from_chain_id: int | None = None
    to_chain_id: int | None = None
    src_tx_status: str | None = None
    dest_tx_status: str | None = None
    settlement_time_seconds: int | None = None
    gas_used: str | None = None
    is_swap_and_bridge: bool = False
    is_partial_tx: bool = False


class MixpanelData(BaseModel):
    events: list[dict] = Field(default_factory=list)
    quote_event_count: int = 0
    first_quote_at: int | None = None
    time_from_first_quote_to_tx_seconds: int | None = None


class TransactionReport(BaseModel):
    tx_hash: str
    order_id: str | None = None
    user_address: str | None = None
    status: str | None = None
    postgres_data: dict | None = None
    loki_data: LokiData | None = None
    quotes: list[QuoteData] = Field(default_factory=list)
    mixpanel_data: MixpanelData | None = None
    anomalies: list[str] = Field(default_factory=list)
    summary: str | None = None
