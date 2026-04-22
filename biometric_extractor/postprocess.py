import json
import re
from datetime import datetime
from typing import Any, Dict, List

from biometric_extractor.models import EMPTY_RECORD, OUTPUT_COLUMNS


CANONICAL_RETROSPECTIVE_EVENT_TYPE = (
    "Retrospective/periodic review of outbreak cases"
)


def parse_llm_records(raw_content: str) -> List[Dict[str, str]]:
    parsed = _parse_json_flexible(raw_content)

    if isinstance(parsed, dict) and isinstance(parsed.get("records"), list):
        records = [
            item for item in parsed["records"] if isinstance(item, dict)
        ]
    elif isinstance(parsed, dict):
        records = [parsed]
    elif isinstance(parsed, list):
        records = [item for item in parsed if isinstance(item, dict)]
    else:
        records = []

    normalized: List[Dict[str, str]] = []
    for record in records:
        normalized.append(_normalize_record(record))

    deduped: List[Dict[str, str]] = []
    seen = set()
    for row in normalized:
        key = tuple(row.get(col, "") for col in OUTPUT_COLUMNS)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    return deduped


def build_empty_result(
    data_source: str,
    source_url: str,
    reason: str = "",
) -> Dict[str, str]:
    row = dict(EMPTY_RECORD)
    row["data_source"] = data_source
    row["source_url"] = source_url
    row["original text"] = reason
    return row


def _parse_json_flexible(raw_content: str) -> Any:
    content = raw_content.strip()
    content = _strip_code_fences(content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    array_match = re.search(r"\[.*\]", content, flags=re.S)
    if array_match:
        return json.loads(array_match.group(0))

    object_match = re.search(r"\{.*\}", content, flags=re.S)
    if object_match:
        return json.loads(object_match.group(0))

    raise ValueError("Cannot parse LLM output to JSON")


def _strip_code_fences(content: str) -> str:
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", content)
        content = re.sub(r"\n```$", "", content)
    return content.strip()


def _normalize_record(record: Dict[str, Any]) -> Dict[str, str]:
    row: Dict[str, str] = dict(EMPTY_RECORD)
    aliases = {
        "original text": ["original_text", "evidence", "evidence_text"],
        "data_source": ["source", "datasource"],
        "source_url": ["url", "source"],
        "location": ["event_location", "occurrence_location"],
        "continent": ["event_continent"],
        "pathogen_old": ["pathogen"],
        "country_old": ["country", "event_country", "location_country"],
        "province_old": ["province", "event_province", "location_province"],
        "original_location": [
            "original location",
            "original_location ",
            "original _location",
            "source_location",
            "infection_origin_location",
        ],
        "original_country_old": [
            "original_country",
            "original country",
            "source_country",
            "infection_origin_country",
        ],
        "imported_location": [
            "imported location",
            "spread_location",
            "destination_location",
        ],
        "imported_country_old": [
            "imported_country",
            "imported country",
            "spread_country",
            "destination_country",
        ],
    }

    for col in OUTPUT_COLUMNS:
        value = record.get(col, "")
        if value in ("", None):
            for alias in aliases.get(col, []):
                alias_value = record.get(alias, "")
                if alias_value not in ("", None):
                    value = alias_value
                    break
        row[col] = _normalize_output_value(col, value)

    row["infection_num"] = _digits_only(row["infection_num"])
    row["death_num"] = _digits_only(row["death_num"])
    row["event_type"] = _normalize_event_type(row["event_type"])

    _fill_date_parts(
        row,
        date_key="start_date",
        year_key="start_date_year",
        month_key="start_date_month",
        day_key="start_date_day",
    )
    _fill_date_parts(
        row,
        date_key="end_date",
        year_key="end_date_year",
        month_key="end_date_month",
        day_key="end_date_day",
    )

    return row


def _normalize_output_value(col: str, value: Any) -> str:
    if value is None:
        return ""

    if col == "location":
        return _normalize_location_value(value)

    if col == "host":
        return _normalize_host_value(value)

    return _to_english_text(str(value).strip())


def _normalize_location_value(value: Any) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            text = _to_english_text(str(item).strip())
            if text:
                parts.append(text)
        return _normalize_location_text("; ".join(parts))

    return _normalize_location_text(_to_english_text(str(value).strip()))


def _normalize_host_value(value: Any) -> str:
    if isinstance(value, list):
        raw_parts = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = _to_english_text(str(value).strip())
        text = text.replace("，", ",").replace("、", ",")
        text = text.replace("；", ";").replace("﹔", ";")
        text = re.sub(r"\s*[\r\n]+\s*", ",", text)
        text = re.sub(r"\s*;\s*", ",", text)
        text = re.sub(r"\s*/\s*", ",", text)
        raw_parts = [part.strip() for part in text.split(",") if part.strip()]

    normalized_parts = []
    seen = set()
    for part in raw_parts:
        normalized = _normalize_host_part(part)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized_parts.append(normalized)

    return ",".join(normalized_parts)


def _normalize_host_part(part: str) -> str:
    cleaned = _to_english_text(part)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;")
    lowered = cleaned.lower()

    if lowered in {"human", "humans", "person", "persons", "people"}:
        return "human"

    if lowered in {"animal", "animals"}:
        return "animal"

    return cleaned


def _normalize_location_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("；", ";").replace("﹔", ";")
    cleaned = re.sub(r"\s*[\r\n]+\s*", "; ", cleaned)
    cleaned = re.sub(r"\s*;\s*", "; ", cleaned)
    cleaned = re.sub(r"(?:;\s*){2,}", "; ", cleaned)
    cleaned = re.sub(r"^;\s*", "", cleaned)
    cleaned = re.sub(r"\s*;$", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _digits_only(value: str) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    return digits


def _normalize_event_type(value: str) -> str:
    if not value:
        return ""

    compact = re.sub(r"[\s_-]+", " ", value).strip()
    lowered = compact.lower()

    if lowered == CANONICAL_RETROSPECTIVE_EVENT_TYPE.lower():
        return CANONICAL_RETROSPECTIVE_EVENT_TYPE

    retrospective_signals = [
        "retrospective",
        "periodic review",
        "review of outbreak cases",
        "outbreak review",
        "historical review",
        "historical summary",
        "cumulative review",
        "cumulative summary",
        "summary of outbreak cases",
    ]
    if any(signal in lowered for signal in retrospective_signals):
        return CANONICAL_RETROSPECTIVE_EVENT_TYPE

    if "sporadic" in lowered or "isolated case" in lowered:
        return "sporadic_case"
    if "pandemic" in lowered:
        return "pandemic"
    if "endemic" in lowered:
        return "endemic"
    if "epidemic" in lowered:
        return "epidemic"
    if "outbreak" in lowered:
        return "outbreak"
    if "cluster" in lowered:
        return "cluster"

    return compact


def _fill_date_parts(
    row: Dict[str, str],
    date_key: str,
    year_key: str,
    month_key: str,
    day_key: str,
) -> None:
    date_text = row.get(date_key, "")

    if not row.get(year_key) or not row.get(month_key) or not row.get(day_key):
        year, month, day = _extract_date_parts(date_text)
        row[year_key] = row[year_key] or year
        row[month_key] = row[month_key] or month
        row[day_key] = row[day_key] or day


def _extract_date_parts(date_text: str) -> List[str]:
    if not date_text:
        return ["", "", ""]

    date_text = date_text.replace("/", "-").replace(".", "-")

    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_text)
    if m:
        return [m.group(1), str(int(m.group(2))), str(int(m.group(3)))]

    m = re.match(r"^(\d{4})-(\d{1,2})$", date_text)
    if m:
        return [m.group(1), str(int(m.group(2))), ""]

    m = re.match(r"^(\d{4})$", date_text)
    if m:
        return [m.group(1), "", ""]

    for fmt in ["%d %B %Y", "%B %d %Y", "%d %b %Y", "%b %d %Y"]:
        try:
            dt = datetime.strptime(date_text, fmt)
            return [str(dt.year), str(dt.month), str(dt.day)]
        except ValueError:
            continue

    return ["", "", ""]


def _to_english_text(text: str) -> str:
    cleaned = re.sub(r"[\u4e00-\u9fff]", "", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()
