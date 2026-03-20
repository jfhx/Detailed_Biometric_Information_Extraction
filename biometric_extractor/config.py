from dataclasses import dataclass
from pathlib import Path


@dataclass
class PipelineConfig:
    input_excel: Path
    output_excel: Path
    output_csv: Path
    log_file: Path
    llm_endpoint: str
    llm_model: str
    timeout_seconds: int = 120
    max_chars_per_source: int = 30000
    max_retries: int = 2
    request_interval_seconds: float = 0.2
    limit: int = 0
