from argparse import ArgumentParser
from pathlib import Path

from biometric_extractor.config import PipelineConfig
from biometric_extractor.pipeline import ExtractionPipeline


def build_args():
    parser = ArgumentParser(
        description=(
            "Extract biological outbreak information from URLs listed in "
            "Excel into location-based outbreak records, where `location` "
            "may be a single place or a semicolon-joined aggregated multi-"
            "place scope, using local DeepSeek-V3 endpoint, with "
            "standardized event_type classification labels."
        )
    )
    parser.add_argument(
        "--input",
        type=str,
        default=(
            "C:/Users/imcas/Desktop/"
            "Detailed_Biometric_Information_Extraction"
            "/source_text_report_gvn.xlsx"
        ),
        help=(
            "Input Excel path (must include columns: data_source, "
            "source_url)."
        ),
    )
    parser.add_argument(
        "--output-excel",
        type=str,
        default=(
            "C:/Users/imcas/Desktop/"
            "Detailed_Biometric_Information_Extraction/out"
            "/biometric_extracted_result.xlsx"
        ),
        help=(
            "Output Excel path for location-based outbreak records "
            "with standardized event_type values and semicolon-joined "
            "multi-place locations when counts are aggregated."
        ),
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=(
            "C:/Users/imcas/Desktop/"
            "Detailed_Biometric_Information_Extraction/out"
            "/biometric_extracted_result.csv"
        ),
        help=(
            "Output CSV path for location-based outbreak records "
            "with standardized event_type values and semicolon-joined "
            "multi-place locations when counts are aggregated."
        ),
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=(
            "C:/Users/imcas/Desktop/"
            "Detailed_Biometric_Information_Extraction/out/logs"
            "/pipeline.log"
        ),
        help="Log file path.",
    )
    parser.add_argument(
        "--status-excel",
        type=str,
        default=(
            "C:/Users/imcas/Desktop/"
            "Detailed_Biometric_Information_Extraction/out"
            "/extraction_runtime_status.xlsx"
        ),
        help="Runtime status Excel path for concise frontend display records.",
    )
    parser.add_argument(
        "--status-csv",
        type=str,
        default=(
            "C:/Users/imcas/Desktop/"
            "Detailed_Biometric_Information_Extraction/out"
            "/extraction_runtime_status.csv"
        ),
        help="Runtime status CSV path for concise frontend display records.",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://159.226.80.101:1045/v1/chat/completions",
        help="Local LLM endpoint.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="DeepSeek-V3",
        help="Model name.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=600,
        help="HTTP timeout (seconds) for web and LLM calls.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retry count for LLM call failures.",
    )
    parser.add_argument(
        "--max-chars-per-source",
        type=int,
        default=30000,
        help="Max characters for body/table text sent to LLM.",
    )
    parser.add_argument(
        "--request-interval-seconds",
        type=float,
        default=0.2,
        help="Sleep interval between URL tasks to reduce burst load.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N URLs (0 means all).",
    )
    parser.add_argument(
        "--record-data-type",
        type=str,
        default="",
        help=(
            "Override runtime status table data type, e.g. "
            "unstructured/semi-structured/structured."
        ),
    )
    parser.add_argument(
        "--record-access-method",
        type=str,
        default="",
        help="Override runtime status table access method, e.g. crawl/API.",
    )
    return parser.parse_args()


def main() -> None:
    args = build_args()
    config = PipelineConfig(
        input_excel=Path(args.input),
        output_excel=Path(args.output_excel),
        output_csv=Path(args.output_csv),
        log_file=Path(args.log_file),
        status_excel=Path(args.status_excel),
        status_csv=Path(args.status_csv),
        llm_endpoint=args.endpoint,
        llm_model=args.model,
        record_data_type=args.record_data_type,
        record_access_method=args.record_access_method,
        timeout_seconds=args.timeout_seconds,
        max_chars_per_source=args.max_chars_per_source,
        max_retries=args.max_retries,
        request_interval_seconds=args.request_interval_seconds,
        limit=args.limit,
    )

    pipeline = ExtractionPipeline(config)
    pipeline.run()


if __name__ == "__main__":
    main()
