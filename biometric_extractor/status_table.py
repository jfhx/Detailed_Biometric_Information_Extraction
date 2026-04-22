from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import urlparse

import pandas as pd

COL_DATA_SOURCE = "\u6570\u636e\u6e90"
COL_DATA_TYPE = "\u6570\u636e\u7c7b\u578b"
COL_ACCESS_METHOD = "\u8c03\u53d6\u65b9\u5f0f"
COL_STATUS = "\u72b6\u6001"
COL_STATUS_NOTE = "\u72b6\u6001\u8bf4\u660e"
COL_START_TIME = "\u5f00\u59cb\u65f6\u95f4"
COL_END_TIME = "\u7ed3\u675f\u65f6\u95f4"
COL_DURATION = "\u7528\u65f6"
COL_CURRENT_DOWNLOAD_SIZE = "\u5f53\u524d\u4e0b\u8f7d\u91cf"
COL_INPUT_COUNT = "\u63d0\u53d6\u524d\uff08\u539f\u59cb\u94fe\u63a5\u6570\u91cf\uff09"
COL_OUTPUT_COUNT = "\u63d0\u53d6\u540e\u6570\u91cf"
COL_EMPTY_PATHOGEN_OLD_COUNT = "\u5f02\u5e38\u6570\uff08pathogen_old\u4e3a\u7a7a\uff09"
COL_STANDARDIZED_COUNT = "\u6807\u51c6\u5316\u8bb0\u5f55\u6570\u91cf"

DATA_TYPE_STRUCTURED = "\u7ed3\u6784\u5316"
DATA_TYPE_SEMI_STRUCTURED = "\u534a\u7ed3\u6784\u5316"
DATA_TYPE_UNSTRUCTURED = "\u975e\u7ed3\u6784\u5316"

ACCESS_METHOD_CRAWL = "\u722c\u53d6"
ACCESS_METHOD_API = "API"

STATUS_STARTED = "\u63d0\u53d6\u5f00\u59cb"
STATUS_SUCCEEDED = "\u63d0\u53d6\u6210\u529f"
STATUS_PARTIAL = "\u90e8\u5206\u6210\u529f"
STATUS_FAILED = "\u63d0\u53d6\u5931\u8d25"

NOTE_STARTED = (
    "\u4efb\u52a1\u5df2\u542f\u52a8\uff0c"
    "\u7b49\u5f85\u63d0\u53d6\u5b8c\u6210"
)
NOTE_ALL_COMPLETED = (
    "\u5168\u90e8\u94fe\u63a5\u63d0\u53d6\u5b8c\u6210"
)

STATUS_TABLE_COLUMNS: List[str] = [
    COL_DATA_SOURCE,
    COL_DATA_TYPE,
    COL_ACCESS_METHOD,
    COL_STATUS,
    COL_STATUS_NOTE,
    COL_START_TIME,
    COL_END_TIME,
    COL_DURATION,
    COL_CURRENT_DOWNLOAD_SIZE,
    COL_INPUT_COUNT,
    COL_OUTPUT_COUNT,
    COL_EMPTY_PATHOGEN_OLD_COUNT,
    COL_STANDARDIZED_COUNT,
]


class RuntimeStatusTableWriter:
    def __init__(self, excel_path: Path, csv_path: Path):
        self.excel_path = excel_path
        self.csv_path = csv_path
        self.rows: List[Dict[str, str]] = []

    def append(self, row: Dict[str, str]) -> None:
        self.rows.append(row)
        self._save()

    def _save(self) -> None:
        self.excel_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        out_df = pd.DataFrame(self.rows)
        out_df = out_df.reindex(columns=STATUS_TABLE_COLUMNS, fill_value="")
        out_df.to_excel(self.excel_path, index=False)
        out_df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")


def build_status_row(
    *,
    data_source: str,
    data_type: str,
    access_method: str,
    status: str,
    status_note: str,
    start_time: datetime,
    end_time: datetime | None = None,
    duration_text: str = "",
    current_download_size: str = "",
    input_count: int | None = None,
    output_count: int | None = None,
    empty_pathogen_old_count: int | None = None,
    standardized_count: int | None = None,
) -> Dict[str, str]:
    return {
        COL_DATA_SOURCE: data_source,
        COL_DATA_TYPE: data_type,
        COL_ACCESS_METHOD: access_method,
        COL_STATUS: status,
        COL_STATUS_NOTE: status_note,
        COL_START_TIME: format_timestamp(start_time),
        COL_END_TIME: format_timestamp(end_time) if end_time else "",
        COL_DURATION: duration_text,
        COL_CURRENT_DOWNLOAD_SIZE: current_download_size,
        COL_INPUT_COUNT: _format_optional_number(input_count),
        COL_OUTPUT_COUNT: _format_optional_number(output_count),
        COL_EMPTY_PATHOGEN_OLD_COUNT: _format_optional_number(
            empty_pathogen_old_count
        ),
        COL_STANDARDIZED_COUNT: _format_optional_number(standardized_count),
    }


def summarize_data_source(values: Iterable[str]) -> str:
    unique_values = []
    seen = set()

    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique_values.append(text)

    if not unique_values:
        return ""
    if len(unique_values) == 1:
        return unique_values[0]
    return "; ".join(unique_values)


def infer_data_type(source_urls: Iterable[str], preferred: str = "") -> str:
    if preferred.strip():
        return preferred.strip()

    categories = Counter(_categorize_url(url) for url in source_urls)
    if not categories:
        return DATA_TYPE_UNSTRUCTURED

    if categories[DATA_TYPE_STRUCTURED] >= max(
        categories[DATA_TYPE_UNSTRUCTURED],
        categories[DATA_TYPE_SEMI_STRUCTURED],
    ):
        return DATA_TYPE_STRUCTURED
    if categories[DATA_TYPE_SEMI_STRUCTURED] >= categories[DATA_TYPE_UNSTRUCTURED]:
        return DATA_TYPE_SEMI_STRUCTURED
    return DATA_TYPE_UNSTRUCTURED


def infer_access_method(source_urls: Iterable[str], preferred: str = "") -> str:
    if preferred.strip():
        return preferred.strip()

    for url in source_urls:
        parsed = urlparse(str(url).strip())
        path = parsed.path.lower()
        query = parsed.query.lower()
        host = parsed.netloc.lower()
        if "/api/" in path or "api." in host or "format=json" in query:
            return ACCESS_METHOD_API
        if path.endswith((".json", ".xml")):
            return ACCESS_METHOD_API

    return ACCESS_METHOD_CRAWL


def format_timestamp(dt: datetime) -> str:
    return f"{dt.year}/{dt.month}/{dt.day}_{dt.strftime('%H:%M:%S')}"


def format_duration(duration: timedelta) -> str:
    total_seconds = max(int(duration.total_seconds()), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: List[str] = []
    if hours:
        parts.append(f"{hours}\u5c0f\u65f6")
    if minutes:
        parts.append(f"{minutes}\u5206\u949f")
    if seconds or not parts:
        parts.append(f"{seconds}\u79d2")
    return "".join(parts)


def summarize_failure_reasons(
    failure_reasons: List[str],
    failed_url_count: int,
) -> str:
    if failed_url_count <= 0:
        return NOTE_ALL_COMPLETED

    normalized_counts = Counter(
        _normalize_failure_reason(reason) for reason in failure_reasons
    )
    top_reasons = [
        f"{reason}{count}\u6761"
        for reason, count in normalized_counts.most_common(3)
        if reason
    ]

    if not top_reasons:
        return (
            f"\u5171{failed_url_count}\u6761\u94fe\u63a5"
            "\u5904\u7406\u5f02\u5e38"
        )

    return (
        f"\u5171{failed_url_count}\u6761\u94fe\u63a5"
        f"\u5904\u7406\u5f02\u5e38\uff1a{'\uff0c'.join(top_reasons)}"
    )


def _categorize_url(url: str) -> str:
    parsed = urlparse(str(url).strip())
    path = parsed.path.lower()
    query = parsed.query.lower()
    host = parsed.netloc.lower()

    if path.endswith((".csv", ".xlsx", ".xls", ".tsv")):
        return DATA_TYPE_STRUCTURED

    if (
        path.endswith((".json", ".xml"))
        or "/api/" in path
        or "api." in host
        or "format=json" in query
        or "format=xml" in query
    ):
        return DATA_TYPE_SEMI_STRUCTURED

    return DATA_TYPE_UNSTRUCTURED


def _normalize_failure_reason(reason: str) -> str:
    text = str(reason).strip()
    if not text:
        return ""

    if "No article body/table content extracted" in text:
        return "\u7f51\u9875\u6b63\u6587\u4e3a\u7a7a"
    if "LLM returned no parseable records" in text:
        return "\u6a21\u578b\u65e0\u53ef\u89e3\u6790\u8bb0\u5f55"
    if "LLM call failed after retries" in text:
        return "\u6a21\u578b\u8c03\u7528\u91cd\u8bd5\u5931\u8d25"
    if text.startswith("ERROR:"):
        if (
            "ReadTimeout" in text
            or "ConnectTimeout" in text
            or "Timeout" in text
        ):
            return "\u8bf7\u6c42\u8d85\u65f6"
        if "ConnectionError" in text:
            return "\u7f51\u7edc\u8fde\u63a5\u5f02\u5e38"
        return "\u811a\u672c\u8fd0\u884c\u5f02\u5e38"

    return text[:30]


def _format_optional_number(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)
