TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "query_metabase_transaction",
            "description": "Query the Bungee backend Postgres database via Metabase to get transaction details, quote history, and user data for a given tx_hash or order_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tx_hash": {"type": "string"},
                    "order_id": {"type": "string"},
                    "user_address": {"type": "string"},
                },
                "anyOf": [
                    {"required": ["tx_hash"]},
                    {"required": ["order_id"]},
                    {"required": ["user_address"]},
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_loki_transaction",
            "description": "Fetch bridge execution data from the Loki transaction API. Returns src and dest tx hashes, bridge name, token amounts, settlement time, gas used, and final status for both source and destination chains.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tx_hash": {"type": "string"},
                },
                "required": ["tx_hash"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mixpanel_events",
            "description": "Retrieve quote and transaction events from Mixpanel for a given user wallet address. Returns all events in a time window around the transaction, showing how many quotes the user requested and which routes were shown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_address": {"type": "string"},
                    "tx_timestamp": {"type": "integer", "description": "Unix seconds"},
                    "window_hours": {"type": "integer", "default": 2},
                },
                "required": ["user_address", "tx_timestamp"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_slippage",
            "description": "Calculate the slippage in basis points between the quoted output amount and the actual output amount received.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quoted_output": {"type": "number"},
                    "actual_output": {"type": "number"},
                    "token_decimals": {"type": "integer"},
                },
                "required": ["quoted_output", "actual_output", "token_decimals"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_settlement_time",
            "description": "Calculate the bridge settlement time in seconds between source and destination chain confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "src_timestamp": {"type": "integer"},
                    "dest_timestamp": {"type": "integer"},
                },
                "required": ["src_timestamp", "dest_timestamp"],
            },
        },
    },
]
