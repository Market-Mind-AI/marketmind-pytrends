import math
from typing import Any

import pandas as pd


def _clean_value(val: Any) -> int | float | None:
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, int | float):
        return val
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return None


def normalize_interest_over_time(df: pd.DataFrame, keyword: str) -> list[dict[str, Any]]:
    if df.empty:
        return []

    records: list[dict[str, Any]] = []
    col = keyword if keyword in df.columns else df.columns[0]
    has_partial = "isPartial" in df.columns

    for idx, row in df.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        value = _clean_value(row[col])
        if value is None:
            value = 0
        is_partial = bool(row["isPartial"]) if has_partial else False
        records.append({"date": date_str, "value": value, "is_partial": is_partial})

    return records


def normalize_interest_by_region(df: pd.DataFrame, keyword: str) -> list[dict[str, Any]]:
    if df.empty:
        return []

    records: list[dict[str, Any]] = []
    col = keyword if keyword in df.columns else df.columns[0]

    for region_name, row in df.iterrows():
        value = _clean_value(row[col])
        if value is None:
            value = 0
        records.append({"region": str(region_name), "value": value})

    return records


def normalize_related_queries(data: dict[str, Any], keyword: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {"top": [], "rising": []}

    kw_data = data.get(keyword, data)

    for query_type in ("top", "rising"):
        df_or_none = kw_data.get(query_type)
        if df_or_none is None or (isinstance(df_or_none, pd.DataFrame) and df_or_none.empty):
            continue
        if isinstance(df_or_none, pd.DataFrame):
            for _, row in df_or_none.iterrows():
                result[query_type].append(
                    {
                        "query": str(row.get("query", "")),
                        "value": _clean_value(row.get("value")),
                    }
                )

    return result


def normalize_related_topics(data: dict[str, Any], keyword: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {"top": [], "rising": []}

    kw_data = data.get(keyword, data)

    for topic_type in ("top", "rising"):
        df_or_none = kw_data.get(topic_type)
        if df_or_none is None or (isinstance(df_or_none, pd.DataFrame) and df_or_none.empty):
            continue
        if isinstance(df_or_none, pd.DataFrame):
            for _, row in df_or_none.iterrows():
                title = str(row.get("topic_title", row.get("title", "")))
                mid = row.get("topic_mid", row.get("mid"))
                value = _clean_value(row.get("value"))
                result[topic_type].append(
                    {
                        "topic": title,
                        "mid": str(mid) if mid else None,
                        "value": value,
                    }
                )

    return result


def normalize_suggestions(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in data:
        result.append(
            {
                "title": str(item.get("title", "")),
                "type": item.get("type"),
                "mid": item.get("mid"),
            }
        )
    return result


def dataframe_to_json_serializable(df: pd.DataFrame) -> dict[str, Any] | list[Any]:
    if df.empty:
        return {}
    df_reset = df.reset_index()
    for col in df_reset.columns:
        if pd.api.types.is_datetime64_any_dtype(df_reset[col]):
            df_reset[col] = df_reset[col].astype(str)
    return df_reset.to_dict(orient="records")  # type: ignore[return-value]


def dict_with_dataframes_to_serializable(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, pd.DataFrame):
            result[key] = dataframe_to_json_serializable(val)
        elif isinstance(val, dict):
            result[key] = dict_with_dataframes_to_serializable(val)
        else:
            result[key] = val
    return result
