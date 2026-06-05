from __future__ import annotations

import os
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class MetabaseQueryError(RuntimeError):
    pass


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


class MetabaseTool:
    def __init__(self) -> None:
        self.base_url = os.getenv("METABASE_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("METABASE_API_KEY", "")
        self.database_id = os.getenv("METABASE_DATABASE_ID", "")

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        reraise=True,
    )
    def query(self, sql: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/dataset"
        headers = {"x-api-key": self.api_key}
        body = {
            "database": int(self.database_id),
            "type": "native",
            "native": {"query": sql},
        }

        response = requests.post(url, headers=headers, json=body, timeout=30)
        if not response.ok:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise MetabaseQueryError(f"Metabase query failed ({response.status_code}): {detail}")
        payload = response.json()

        data = payload.get("data")
        if not data:
            return []

        cols = data.get("cols") or []
        rows = data.get("rows") or []
        if not rows:
            return []

        col_names = [col.get("name") for col in cols]
        return [dict(zip(col_names, row, strict=False)) for row in rows]

    def get_transaction_by_hash(self, tx_hash: str) -> dict[str, Any] | None:
        tx_hash = _sql_literal(tx_hash)
        sql = f"""
SELECT
  br.id,
  br."requestHash" AS order_id,
  br."requestHash" AS request_hash,
  br."quoteId" AS quote_id,
  COALESCE(
    br."extractionTxHash",
    br."fulfilmentTxHash",
    br."settlementTxHash",
    br."swapTxHash",
    br."withdrawOnDestinationTxHash",
    br."withdrawOnSourceTxHash",
    br."inboxCreatedTxHash",
    br."inboxWithdrawnTxHash"
  ) AS tx_hash,
  COALESCE(
    br."fulfilmentTxHash",
    br."settlementTxHash",
    br."withdrawOnDestinationTxHash",
    br."inboxWithdrawnTxHash"
  ) AS dest_tx_hash,
  CASE
    WHEN br."failureReason" IS NOT NULL THEN 'FAILED'
    WHEN br."withdrawOnDestinationTxHash" IS NOT NULL
      OR br."fulfilmentTxHash" IS NOT NULL
      OR br."settlementTxHash" IS NOT NULL
      OR br."fulfillmentTimestamp" IS NOT NULL THEN 'COMPLETED'
    WHEN br."cancelledTxHash" IS NOT NULL THEN 'CANCELLED'
    ELSE 'PENDING'
  END AS status,
  br."originChainId" AS from_chain_id,
  br."destinationChainId" AS to_chain_id,
  br."inputToken" AS src_token_address,
  br."outputToken" AS dest_token_address,
  br."inputAmount" AS src_amount,
  br."fulfilAmount" AS dest_amount,
  COALESCE(
    br."swapActualFeeUSD",
    br."fulfilmentActualFeeUSD",
    br."settlementActualFeeUSD",
    br."extractionActualFeeUSD",
    br."swapEstimatedFeeUSD",
    br."fulfilmentEstimatedFeeUSD",
    br."settlementEstimatedFeeUSD",
    br."extractionEstimatedFeeUSD"
  ) AS fee,
  br."routerType" AS bridge_name,
  qres."userAddress" AS user_address,
  qres."receiverAddress" AS recipient,
  qres."outputAmountInUSD" AS output_amount_usd,
  CASE
    WHEN br."swapTxHash" IS NOT NULL
      AND br."inboxCreatedTxHash" IS NULL
      AND br."originChainId" = br."destinationChainId"
      AND br."requestType" = 'SWAP_REQUEST'
      THEN 'SUBMIT Same Chain'
    WHEN br."extractionTxHash" IS NOT NULL
      AND br."fulfilmentTxHash" IS NOT NULL
      AND br."swapTxHash" IS NULL
      AND br."inboxCreatedTxHash" IS NULL
      AND br."requestType" = 'SINGLE_OUTPUT_REQUEST'
      THEN 'SUBMIT X-Chain'
    WHEN br."swapTxHash" IS NOT NULL
      AND br."inboxCreatedTxHash" IS NOT NULL
      AND br."originChainId" = br."destinationChainId"
      AND br."requestType" = 'SWAP_REQUEST'
      THEN 'Inbox Same Chain'
    WHEN br."extractionTxHash" IS NOT NULL
      AND br."fulfilmentTxHash" IS NOT NULL
      AND br."swapTxHash" IS NULL
      AND br."inboxCreatedTxHash" IS NOT NULL
      AND br."requestType" = 'SINGLE_OUTPUT_REQUEST'
      THEN 'Inbox X-Chain'
  END AS transaction_type,
  br."createdAt" AS created_at,
  br."updatedAt" AS updated_at
FROM bungee_request br
LEFT JOIN quote_response qres ON qres."quoteId" = br."quoteId"
WHERE
  br."extractionTxHash" = '{tx_hash}'
  OR br."fulfilmentTxHash" = '{tx_hash}'
  OR br."settlementTxHash" = '{tx_hash}'
  OR br."swapTxHash" = '{tx_hash}'
  OR br."withdrawOnDestinationTxHash" = '{tx_hash}'
  OR br."withdrawOnSourceTxHash" = '{tx_hash}'
  OR br."cancelledTxHash" = '{tx_hash}'
  OR br."inboxCreatedTxHash" = '{tx_hash}'
  OR br."inboxWithdrawnTxHash" = '{tx_hash}'
LIMIT 1
"""
        rows = self.query(sql)
        return rows[0] if rows else None

    def get_transaction_by_request_hash(self, request_hash: str) -> dict[str, Any] | None:
        request_hash = _sql_literal(request_hash)
        sql = f"""
SELECT
  br.id,
  br."requestHash" AS order_id,
  br."requestHash" AS request_hash,
  br."quoteId" AS quote_id,
  COALESCE(
    br."extractionTxHash",
    br."fulfilmentTxHash",
    br."settlementTxHash",
    br."swapTxHash",
    br."withdrawOnDestinationTxHash",
    br."withdrawOnSourceTxHash",
    br."inboxCreatedTxHash",
    br."inboxWithdrawnTxHash"
  ) AS tx_hash,
  COALESCE(
    br."fulfilmentTxHash",
    br."settlementTxHash",
    br."withdrawOnDestinationTxHash",
    br."inboxWithdrawnTxHash"
  ) AS dest_tx_hash,
  CASE
    WHEN br."failureReason" IS NOT NULL THEN 'FAILED'
    WHEN br."withdrawOnDestinationTxHash" IS NOT NULL
      OR br."fulfilmentTxHash" IS NOT NULL
      OR br."settlementTxHash" IS NOT NULL
      OR br."fulfillmentTimestamp" IS NOT NULL THEN 'COMPLETED'
    WHEN br."cancelledTxHash" IS NOT NULL THEN 'CANCELLED'
    ELSE 'PENDING'
  END AS status,
  br."originChainId" AS from_chain_id,
  br."destinationChainId" AS to_chain_id,
  br."inputToken" AS src_token_address,
  br."outputToken" AS dest_token_address,
  br."inputAmount" AS src_amount,
  br."fulfilAmount" AS dest_amount,
  COALESCE(
    br."swapActualFeeUSD",
    br."fulfilmentActualFeeUSD",
    br."settlementActualFeeUSD",
    br."extractionActualFeeUSD",
    br."swapEstimatedFeeUSD",
    br."fulfilmentEstimatedFeeUSD",
    br."settlementEstimatedFeeUSD",
    br."extractionEstimatedFeeUSD"
  ) AS fee,
  br."routerType" AS bridge_name,
  qres."userAddress" AS user_address,
  qres."receiverAddress" AS recipient,
  qres."outputAmountInUSD" AS output_amount_usd,
  CASE
    WHEN br."swapTxHash" IS NOT NULL
      AND br."inboxCreatedTxHash" IS NULL
      AND br."originChainId" = br."destinationChainId"
      AND br."requestType" = 'SWAP_REQUEST'
      THEN 'SUBMIT Same Chain'
    WHEN br."extractionTxHash" IS NOT NULL
      AND br."fulfilmentTxHash" IS NOT NULL
      AND br."swapTxHash" IS NULL
      AND br."inboxCreatedTxHash" IS NULL
      AND br."requestType" = 'SINGLE_OUTPUT_REQUEST'
      THEN 'SUBMIT X-Chain'
    WHEN br."swapTxHash" IS NOT NULL
      AND br."inboxCreatedTxHash" IS NOT NULL
      AND br."originChainId" = br."destinationChainId"
      AND br."requestType" = 'SWAP_REQUEST'
      THEN 'Inbox Same Chain'
    WHEN br."extractionTxHash" IS NOT NULL
      AND br."fulfilmentTxHash" IS NOT NULL
      AND br."swapTxHash" IS NULL
      AND br."inboxCreatedTxHash" IS NOT NULL
      AND br."requestType" = 'SINGLE_OUTPUT_REQUEST'
      THEN 'Inbox X-Chain'
  END AS transaction_type,
  br."createdAt" AS created_at,
  br."updatedAt" AS updated_at
FROM bungee_request br
LEFT JOIN quote_response qres ON qres."quoteId" = br."quoteId"
WHERE
  br."requestHash" = '{request_hash}'
LIMIT 1
"""
        rows = self.query(sql)
        return rows[0] if rows else None

    def get_quotes_for_order(self, quote_id: str) -> list[dict[str, Any]]:
        quote_id = _sql_literal(quote_id)
        sql = f"""
SELECT
  qres."serverRequestId" AS quote_request_id,
  qres."userAddress" AS user_address,
  qres."originChainId" AS from_chain_id,
  qres."destinationChainId" AS to_chain_id,
  qres."inputTokenAddress" AS src_token_address,
  qres."outputTokenAddress" AS dest_token_address,
  qres."inputAmountParsed" AS src_amount,
  qres."createdAt" AS quoted_at,
  qres."routerName" AS route,
  COALESCE(qres."routerName", qres."dexProtocolName") AS bridge_name,
  NULLIF(qres."outputAmountParsed", '')::numeric AS quoted_output,
  NULLIF(qres."affiliateFeeParsedAmount", '')::numeric AS quoted_fee,
  NULL::integer AS estimated_time,
  qres."quoteId" AS order_id,
  qres."serverRequestId" AS server_request_id,
  qres."inputTokenSymbol" AS src_token_symbol,
  qres."outputTokenSymbol" AS dest_token_symbol
FROM quote_response qres
WHERE qres."quoteId" = '{quote_id}'
ORDER BY qres."createdAt" DESC
"""
        return self.query(sql)

    def get_pending_transactions(self) -> list[dict[str, Any]]:
        sql = """
SELECT
    'Inbox Pending, Not extracted' as type,
    bungee_request."requestHash" as request_hash,
    bungee_request."requestType" as request_type,
    bungee_request."requestReceivedAt" as request_received_at,
    bungee_request."originChainId" as origin_chain_id,
    bungee_request."destinationChainId" as destination_chain_id,
    bungee_request."inputToken" as input_token,
    bungee_request."outputToken" as output_token,
    bungee_request."inputAmount" as input_amount,
    bungee_request."createdAt" as created_at,
    bungee_request."updatedAt" as updated_at,
    bungee_request."extractionTimestamp" as extraction_timestamp,
    bungee_request."routerType" as router_type,
    bungee_request."failureReason" as failure_reason,
    bungee_request."quoteId" as quote_id,
    qr."integratorName" AS integrator_name,
    qr."inputTokenSymbol" as input_token_symbol,
    qr."outputTokenSymbol" as output_token_symbol,
    qr."inputAmountInUSD" as input_amount_usd,
    qr."outputAmountInUSD" as output_amount_usd,
    EXTRACT(EPOCH FROM (bungee_request."updatedAt" - bungee_request."extractionTimestamp")) / 60 AS pending_mins
FROM public.bungee_request
LEFT JOIN public.quote_response qr
ON bungee_request."quoteId" = qr."quoteId"
WHERE "extractionTxHash" is null
    AND "fulfilmentTxHash" is null
    AND "swapTxHash" is null
    AND "inboxWithdrawnTxHash" is null
    AND "cancelledTxHash" is null
    AND "inboxCreatedTxHash" is not null
    AND bungee_request."createdAt" >= NOW() - INTERVAL '10 days'

UNION ALL

SELECT
    'Inbox Cancelled but not Withdrawn' as type,
    br."requestHash" as request_hash,
    br."requestType" as request_type,
    br."requestReceivedAt" as request_received_at,
    br."originChainId" as origin_chain_id,
    br."destinationChainId" as destination_chain_id,
    br."inputToken" as input_token,
    br."outputToken" as output_token,
    br."inputAmount" as input_amount,
    br."createdAt" as created_at,
    br."updatedAt" as updated_at,
    br."extractionTimestamp" as extraction_timestamp,
    br."routerType" as router_type,
    br."failureReason" as failure_reason,
    br."quoteId" as quote_id,
    qr."integratorName" AS integrator_name,
    qr."inputTokenSymbol" as input_token_symbol,
    qr."outputTokenSymbol" as output_token_symbol,
    qr."inputAmountInUSD" as input_amount_usd,
    qr."outputAmountInUSD" as output_amount_usd,
    EXTRACT(EPOCH FROM (NOW() - br."extractionTimestamp")) / 60 AS pending_mins
FROM public.bungee_request br
LEFT JOIN public.quote_response qr
ON br."quoteId" = qr."quoteId"
WHERE br."extractionTxHash" IS NOT NULL
    AND br."fulfilmentTxHash" IS NULL
    AND br."inboxWithdrawnTxHash" IS NULL
    AND br."cancelledTxHash" IS NOT NULL
    AND br."inboxCreatedTxHash" is not NULL
    AND br."createdAt" >= NOW() - INTERVAL '10 days'

UNION ALL

SELECT
    'Token Extracted but not fulfilled' as type,
    bungee_request."requestHash" as request_hash,
    bungee_request."requestType" as request_type,
    bungee_request."requestReceivedAt" as request_received_at,
    bungee_request."originChainId" as origin_chain_id,
    bungee_request."destinationChainId" as destination_chain_id,
    bungee_request."inputToken" as input_token,
    bungee_request."outputToken" as output_token,
    bungee_request."inputAmount" as input_amount,
    bungee_request."createdAt" as created_at,
    bungee_request."updatedAt" as updated_at,
    bungee_request."extractionTimestamp" as extraction_timestamp,
    bungee_request."routerType" as router_type,
    bungee_request."failureReason" as failure_reason,
    bungee_request."quoteId" as quote_id,
    qr."integratorName" AS integrator_name,
    qr."inputTokenSymbol" as input_token_symbol,
    qr."outputTokenSymbol" as output_token_symbol,
    qr."inputAmountInUSD" as input_amount_usd,
    qr."outputAmountInUSD" as output_amount_usd,
    EXTRACT(EPOCH FROM (NOW() - bungee_request."extractionTimestamp")) / 60 AS pending_mins
FROM public.bungee_request
LEFT JOIN public.quote_response qr
ON bungee_request."quoteId" = qr."quoteId"
WHERE bungee_request."extractionTxHash" IS NOT NULL
    AND bungee_request."fulfilmentTxHash" IS NULL
    AND bungee_request."swapTxHash" IS NULL
    AND bungee_request."inboxWithdrawnTxHash" IS NULL
    AND bungee_request."cancelledTxHash" IS NULL
    AND bungee_request."inboxCreatedTxHash" is NULL
    AND bungee_request."withdrawOnDestinationTxHash" IS NULL
    AND bungee_request."withdrawOnSourceTxHash" is NULL
    AND bungee_request."createdAt" >= NOW() - INTERVAL '10 days'

UNION ALL

SELECT
    'Token Extracted but not fulfilled (Inbox Created)' as type,
    bungee_request."requestHash" as request_hash,
    bungee_request."requestType" as request_type,
    bungee_request."requestReceivedAt" as request_received_at,
    bungee_request."originChainId" as origin_chain_id,
    bungee_request."destinationChainId" as destination_chain_id,
    bungee_request."inputToken" as input_token,
    bungee_request."outputToken" as output_token,
    bungee_request."inputAmount" as input_amount,
    bungee_request."createdAt" as created_at,
    bungee_request."updatedAt" as updated_at,
    bungee_request."extractionTimestamp" as extraction_timestamp,
    bungee_request."routerType" as router_type,
    bungee_request."failureReason" as failure_reason,
    bungee_request."quoteId" as quote_id,
    qr."integratorName" AS integrator_name,
    qr."inputTokenSymbol" as input_token_symbol,
    qr."outputTokenSymbol" as output_token_symbol,
    qr."inputAmountInUSD" as input_amount_usd,
    qr."outputAmountInUSD" as output_amount_usd,
    EXTRACT(EPOCH FROM (NOW() - bungee_request."extractionTimestamp")) / 60 AS pending_mins
FROM public.bungee_request
LEFT JOIN public.quote_response qr
ON bungee_request."quoteId" = qr."quoteId"
WHERE bungee_request."extractionTxHash" IS NOT NULL
    AND bungee_request."fulfilmentTxHash" IS NULL
    AND bungee_request."swapTxHash" IS NULL
    AND bungee_request."inboxWithdrawnTxHash" IS NULL
    AND bungee_request."cancelledTxHash" IS NULL
    AND bungee_request."inboxCreatedTxHash" IS NOT NULL
    AND bungee_request."withdrawOnDestinationTxHash" IS NULL
    AND bungee_request."withdrawOnSourceTxHash" IS NULL
    AND bungee_request."createdAt" >= NOW() - INTERVAL '10 days'
ORDER BY request_received_at DESC
"""
        return self.query(sql)
