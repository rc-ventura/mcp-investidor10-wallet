_enabled = False

SUMMARY_FIELDS = frozenset(
    {"type", "variation", "profit_twr", "profit_twr_12m", "currency"}
)
ALLOCATION_FIELDS = frozenset({"name", "type", "percent"})
POSITIONS_TOP_FIELDS = frozenset({"total", "draw", "truncated"})
POSITION_ROW_FIELDS = frozenset(
    {
        "id",
        "tickerable_id",
        "ticker",
        "ticker_name",
        "ticker_type",
        "currency",
        "url",
        "image",
        "country",
        "iso_alpha_2",
        "segment",
        "fii_type",
        "percent_wallet",
        "percent_ideal",
        "buy",
        "avg_price",
        "user_avg_price",
        "avg_price_treasure",
        "current_price",
        "current_price_treasure",
        "target_price",
        "appreciation",
        "weighted_return",
        "profitability",
        "yoc",
        "dy",
        "dividend_yield_last_5_years",
        "payout",
        "p_l",
        "p_vp",
        "roe",
        "net_margin",
        "gross_margin",
        "profit_1",
        "profit_7",
        "profit_30",
        "profit_365",
        "rating",
        "raw_rating",
        "avg_rating",
        "raw_avg_rating",
        "checklist_rate",
        "graham",
        "bazin",
        "vacancy",
        "quotes_count",
        "shareholders",
        "net_worth",
        "last_yield",
        "equity_per_share",
        "capitalization",
        "is_calculating_rentability",
    }
)


def configure(config: dict) -> None:
    global _enabled
    _enabled = bool(config.get("mask_values", False))


def enabled() -> bool:
    return _enabled


def _keep(mapping: dict, allowed: frozenset, omitted: set) -> dict:
    kept = {}
    for key, value in mapping.items():
        if key in allowed and not isinstance(value, (dict, list)):
            kept[key] = value
        else:
            omitted.add(key)
    return kept


def _keep_items(items: list, allowed: frozenset, omitted: set) -> list:
    return [_keep(item, allowed, omitted) for item in items if isinstance(item, dict)]


def mask(tool: str, envelope: dict) -> dict:
    if not _enabled:
        return envelope
    omitted: set = set()
    data = envelope["data"]
    if tool == "summary":
        masked = _keep(data, SUMMARY_FIELDS, omitted)
    elif tool == "allocation":
        masked = _keep_items(data, ALLOCATION_FIELDS, omitted)
    else:
        rows = data.get("data", [])
        top = {key: value for key, value in data.items() if key != "data"}
        masked = _keep(top, POSITIONS_TOP_FIELDS, omitted)
        masked["data"] = _keep_items(rows, POSITION_ROW_FIELDS, omitted)
    result = {key: value for key, value in envelope.items() if key != "data"}
    result["privacy"] = {"masked": True, "omitted": sorted(omitted)}
    result["data"] = masked
    return result


def unavailable_error(tool: str) -> dict:
    return {
        "error": {
            "code": "privacy_mode_unavailable",
            "message": (
                f"{tool} is unavailable: the operator enabled privacy mode, which "
                "withholds monetary amounts. Use get_wallet_allocation or "
                "get_wallet_positions for percentage-based analysis; do not estimate "
                "the withheld amounts."
            ),
        }
    }
