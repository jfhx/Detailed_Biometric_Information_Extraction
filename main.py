from argparse import ArgumentParser
from pathlib import Path

from biometric_extractor.config import PipelineConfig
from biometric_extractor.pipeline import ExtractionPipeline


def build_args():
    parser = ArgumentParser(
        description=(
            "Extract biological outbreak information from URLs listed in "
            "Excel into location-based outbreak records, using local "
            "DeepSeek-V3 endpoint."
        )
    )
    parser.add_argument(
        "--input",
        type=str,
        default=r"C:\Users\imcas\Desktop\Detailed_Biometric_Information_Extraction\source_text_report.xlsx",
        help="Input Excel path (must include columns: data_source, source_url).",
    )
    parser.add_argument(
        "--output-excel",
        type=str,
        default=r"C:\Users\imcas\Desktop\Detailed_Biometric_Information_Extraction\out\biometric_extracted_result.xlsx",
        help="Output Excel path for location-based outbreak records.",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=r"C:\Users\imcas\Desktop\Detailed_Biometric_Information_Extraction\out\biometric_extracted_result.csv",
        help="Output CSV path for location-based outbreak records.",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=r"C:\Users\imcas\Desktop\Detailed_Biometric_Information_Extraction\out\logs\pipeline.log",
        help="Log file path.",
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
        default=120,
        help="HTTP timeout (seconds) for web and LLM calls.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
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
    return parser.parse_args()


def main() -> None:
    args = build_args()
    config = PipelineConfig(
        input_excel=Path(args.input),
        output_excel=Path(args.output_excel),
        output_csv=Path(args.output_csv),
        log_file=Path(args.log_file),
        llm_endpoint=args.endpoint,
        llm_model=args.model,
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
