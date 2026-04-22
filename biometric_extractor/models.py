from typing import Dict, List


OUTPUT_COLUMNS: List[str] = [
    "data_source",
    "source_url",
    "pathogen_type",
    "pathogen_old",
    "subtype",
    "location",
    "continent",
    "country_old",
    "province_old",
    "original_location",
    "original_country_old",
    "imported_location",
    "imported_country_old",
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
