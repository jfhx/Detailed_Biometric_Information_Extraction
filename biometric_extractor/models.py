from typing import Dict, List


OUTPUT_COLUMNS: List[str] = [
    "data_source",
    "source_url",
    "pathogen_type",
    "pathogen",
    "subtype",
    "location",
    "continent",
    "country",
    "province",
    "original_location",
    "original_country",
    "imported_location",
    "imported_country",
    "start_date",
    "start_date_year",
    "start_date_month",
    "start_date_day",
    "end_date",
    "end_date_year",
    "end_date_month",
    "end_date_day",
    "host",
    "infection_num",
    "death_num",
    "event_type",
    "original text",
]


EMPTY_RECORD: Dict[str, str] = {column: "" for column in OUTPUT_COLUMNS}
