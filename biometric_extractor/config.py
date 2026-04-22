from dataclasses import dataclass
from pathlib import Path


@dataclass
class PipelineConfig:
    input_excel: Path
    output_excel: Path
    output_csv: Path
    log_file: Path
    status_excel: Path
    status_csv: Path
    llm_endpoint: str
    llm_model: str
    record_data_type: str = ""
    record_access_method: str = ""
    timeout_seconds: int = 600
    max_chars_per_source: int = 30000
    max_retries: int = 2
    request_interval_seconds: float = 0.2
    limit: int = 0
