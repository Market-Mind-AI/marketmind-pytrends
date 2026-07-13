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


def normalize_interest_by_country(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Normalize the long-format worldwide matrix produced by the client
    (one row per country/term on a single common axis) into persistable
    records. Null/NaN values are coerced to 0."""
    if df.empty:
        return []

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        value = _clean_value(row["value"])
        if value is None:
            value = 0
        records.append(
            {
                "country": str(row["country"]),
                "term": str(row["term"]),
                "term_language": str(row["term_language"]),
                "value": value,
            }
        )

    return records


def normalize_interest_by_region_worldwide(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Normalize the long-format worldwide sub-national matrix produced by the
    client (one row per region/term on a single common axis) into persistable
    records. Null/NaN interest values are coerced to 0; a missing region_name
    stays None."""
    if df.empty:
        return []

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        value = _clean_value(row["value"])
        if value is None:
            value = 0
        region_name = row["region_name"] if "region_name" in df.columns else None
        records.append(
            {
                "country": str(row["country"]),
                "region_code": str(row["region_code"]),
                "region_name": None if region_name is None or pd.isna(region_name) else str(region_name),
                "term": str(row["term"]),
                "term_language": str(row["term_language"]),
                "value": value,
            }
        )

    return records


def build_anchor_batches(terms: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    """Split (term, language) pairs into Google-Trends-compatible batches of at
    most 5 terms. If more than 5 terms are given, terms[0] is the anchor and is
    prepended to every batch after the first, so all batches share a common term
    for cross-batch rescaling (anchor-chaining). Batch 1 is terms[0:5]; each
    subsequent batch is [anchor] + the next up-to-4 terms."""
    if len(terms) <= 5:
        return [list(terms)]
    anchor = terms[0]
    batches = [list(terms[:5])]
    rest = list(terms[5:])
    for i in range(0, len(rest), 4):
        batches.append([anchor, *rest[i : i + 4]])
    return batches


def merge_anchor_batches(frames: list[pd.DataFrame], anchor_term: str) -> pd.DataFrame:
    """Merge per-batch long-format frames (columns country/term/term_language/
    value) onto batch 1's common axis using the shared anchor term.

    Scaling factor for batch k (k > 1):
        factor_k = (anchor's global max value in batch 1)
                   / (anchor's global max value in batch k)
    The anchor's maximum value across countries is used as the robust reference
    cell. Every value in batch k is multiplied by factor_k, then the anchor's
    own rows in batch k are dropped (batch 1's anchor rows are kept) to
    deduplicate. If the anchor's max in batch k is 0 (no signal to scale
    against), factor_k is 0.0. Scaled values are intentionally NOT clamped to
    [0, 100] — comparable ratios can legitimately exceed 100 after rescaling."""
    columns = ["country", "term", "term_language", "value"]
    if not frames:
        return pd.DataFrame(columns=columns)

    reference_frame = frames[0]
    ref_anchor = reference_frame.loc[reference_frame["term"] == anchor_term, "value"]
    reference = float(ref_anchor.max()) if not ref_anchor.empty else 0.0

    merged = [reference_frame]
    for frame in frames[1:]:
        anchor_vals = frame.loc[frame["term"] == anchor_term, "value"]
        anchor_max = float(anchor_vals.max()) if not anchor_vals.empty else 0.0
        factor = reference / anchor_max if anchor_max > 0 else 0.0
        scaled = frame.loc[frame["term"] != anchor_term].copy()
        scaled["value"] = scaled["value"] * factor
        merged.append(scaled)
    return pd.concat(merged, ignore_index=True)


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
