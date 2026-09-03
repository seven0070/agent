"""Inspect JSON/CSV workspace records and answer aggregation questions."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Dict, List, Optional, Union


def _as_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        records = []
        for item in payload:
            if isinstance(item, dict):
                records.append(item)
        return records
    if isinstance(payload, dict):
        for value in payload.values():
            nested = _as_records(value)
            if nested:
                return nested
        return [payload]
    return []


def _parse_records(raw: str) -> List[Dict[str, Any]]:
    text = raw.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        records = _as_records(parsed)
        if records:
            return records
    except json.JSONDecodeError:
        pass
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames:
        return [dict(row) for row in reader]
    return []


def _numeric(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _numeric_fields(records: List[Dict[str, Any]]) -> List[str]:
    fields: List[str] = []
    for key in records[0].keys():
        if any(_numeric(row.get(key)) is not None for row in records):
            fields.append(key)
    return fields


def inspect_structured_data(raw: str, query: str) -> str:
    """Answer min/max-style questions about JSON or CSV records."""
    records = _parse_records(raw)
    if not records:
        raise ValueError("No structured records found in the provided data.")

    lower = query.lower()
    want_count = bool(re.search(r"\b(how many|count|number of)\b", lower))
    want_avg = bool(re.search(r"\b(average|mean)\b", lower))
    want_sum = bool(re.search(r"\b(total|sum)\b", lower))
    want_summary = bool(re.search(r"\b(summarize|summary)\b", lower))
    want_max = bool(re.search(r"\b(highest|max|largest|most|top)\b", lower))
    want_min = bool(re.search(r"\b(lowest|min|smallest|least|bottom)\b", lower))
    if want_count and not (want_avg or want_max or want_min or want_sum or want_summary):
        return f"{len(records)} records."

    fields = _numeric_fields(records)
    if not fields:
        return json.dumps(records, indent=2)

    field = next((key for key in fields if key.lower() in lower), fields[0])
    scored = [(row, _numeric(row.get(field))) for row in records]
    scored = [(row, value) for row, value in scored if value is not None]
    if not scored:
        return json.dumps(records, indent=2)

    if want_avg:
        avg = sum(value for _, value in scored) / len(scored)
        rendered = avg if avg != int(avg) else int(avg)
        return f"The average {field} is {rendered}."

    if want_sum and not (want_max or want_min):
        total = sum(value for _, value in scored)
        rendered = total if total != int(total) else int(total)
        return f"The total {field} is {rendered}."

    if want_summary and not (want_max or want_min or want_avg):
        total = sum(value for _, value in scored)
        avg = total / len(scored)
        winner, value = max(scored, key=lambda item: item[1])
        identity = next((v for k, v in winner.items() if k != field), winner)
        avg_r = avg if avg != int(avg) else int(avg)
        tot_r = total if total != int(total) else int(total)
        val_r = value if value != int(value) else int(value)
        return (
            f"{len(records)} records. Total {field} {tot_r}. "
            f"Average {field} {avg_r}. Highest {field} {identity} ({val_r})."
        )

    if want_min and not want_max:
        winner, value = min(scored, key=lambda item: item[1])
        agg = "lowest"
    else:
        winner, value = max(scored, key=lambda item: item[1])
        agg = "highest"

    identity = None
    for key, item in winner.items():
        if key == field:
            continue
        if key.lower() in lower or key.lower() in {"user", "name", "id", "player"}:
            identity = item
            break
    if identity is None:
        identity = next((v for k, v in winner.items() if k != field), winner)

    rendered = value if value != int(value) else int(value)
    return f"{identity} has the {agg} {field} ({rendered}).\n{json.dumps(winner)}"
