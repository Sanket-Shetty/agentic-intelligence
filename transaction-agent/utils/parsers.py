from __future__ import annotations


def human_readable_amount(raw_amount: str, decimals: int) -> float:
    return round(int(raw_amount) / (10**decimals), 6)


def slippage_bps(quoted_output: float, actual_output: float) -> float:
    return round(((actual_output - quoted_output) / quoted_output) * 10000, 2)


def chain_id_to_name(chain_id: int) -> str:
    chain_names = {
        1: "Ethereum",
        56: "BSC",
        137: "Polygon",
        42161: "Arbitrum",
        10: "Optimism",
        8453: "Base",
        43114: "Avalanche",
        250: "Fantom",
        100: "Gnosis",
    }
    return chain_names.get(chain_id, f"Chain {chain_id}")
