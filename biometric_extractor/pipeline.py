import time
from datetime import datetime
from typing import Dict, List

from biometric_extractor.config import PipelineConfig
from biometric_extractor.fetcher import ArticleFetcher
from biometric_extractor.io_utils import read_input_rows, save_output
from biometric_extractor.llm_client import LLMClient
from biometric_extractor.logging_utils import format_size, setup_logger
from biometric_extractor.postprocess import build_empty_result, parse_llm_records
from biometric_extractor.prompts import SYSTEM_PROMPT, build_user_prompt
from biometric_extractor.status_table import (
    NOTE_STARTED,
    RuntimeStatusTableWriter,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_STARTED,
    STATUS_SUCCEEDED,
    build_status_row,
    format_duration,
    infer_access_method,
    infer_data_type,
    summarize_data_source,
    summarize_failure_reasons,
)


class ExtractionPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = setup_logger(config.log_file)
        self.fetcher = ArticleFetcher(
            timeout_seconds=config.timeout_seconds,
            max_chars=config.max_chars_per_source,
        )
        self.llm_client = LLMClient(
            endpoint=config.llm_endpoint,
            model=config.llm_model,
            timeout_seconds=config.timeout_seconds,
        )

    def run(self) -> List[Dict[str, str]]:
        start_time = datetime.now()
        in_df = read_input_rows(self.config.input_excel)
        if self.config.limit > 0:
            in_df = in_df.head(self.config.limit).copy()
        self.logger.info("Input rows loaded: %s", len(in_df))

        source_urls = in_df["source_url"].tolist()
        data_source_summary = summarize_data_source(
            in_df["data_source"].tolist()
        )
        data_type = infer_data_type(
            source_urls,
            preferred=self.config.record_data_type,
        )
        access_method = infer_access_method(
            source_urls,
            preferred=self.config.record_access_method,
        )

        status_writer = RuntimeStatusTableWriter(
            excel_path=self.config.status_excel,
            csv_path=self.config.status_csv,
        )
        status_writer.append(
            build_status_row(
                data_source=data_source_summary,
                data_type=data_type,
                access_method=access_method,
                status=STATUS_STARTED,
                status_note=NOTE_STARTED,
                start_time=start_time,
                input_count=len(in_df),
            )
        )
        self.logger.info(
            "Runtime status table initialized: %s",
            self.config.status_excel,
        )

        all_rows: List[Dict[str, str]] = []
        failure_reasons: List[str] = []
        failed_url_count = 0

        try:
            for idx, row in in_df.iterrows():
                data_source = row["data_source"]
                source_url = row["source_url"]
                self.logger.info(
                    "[%s/%s] Processing: %s",
                    idx + 1,
                    len(in_df),
                    source_url,
                )

                try:
                    records = self._process_single(data_source, source_url)
                except Exception as exc:
                    self.logger.exception(
                        "Failed to process URL: %s | error=%s",
                        source_url,
                        exc,
                    )
                    records = [
                        build_empty_result(
                            data_source,
                            source_url,
                            reason=f"ERROR: {type(exc).__name__}: {exc}",
                        )
                    ]

                failure_reason = self._extract_failure_reason(records)
                if failure_reason:
                    failed_url_count += 1
                    failure_reasons.append(failure_reason)

                all_rows.extend(records)
                time.sleep(self.config.request_interval_seconds)

            out_df = save_output(
                all_rows,
                self.config.output_excel,
                self.config.output_csv,
            )
            empty_pathogen_old_count = self._count_empty_pathogen_old(all_rows)
            dataframe_memory_bytes = int(out_df.memory_usage(deep=True).sum())
            self.logger.info("Pipeline completed. Output rows: %s", len(all_rows))
            self.logger.info(
                "Output rows with empty pathogen_old: %s",
                empty_pathogen_old_count,
            )
            self.logger.info("Excel output: %s", self.config.output_excel)
            self.logger.info(
                "Excel output size: %s",
                format_size(self.config.output_excel.stat().st_size),
            )
            self.logger.info("CSV output: %s", self.config.output_csv)
            self.logger.info(
                "CSV output size: %s",
                format_size(self.config.output_csv.stat().st_size),
            )
            self.logger.info(
                "Output table memory estimate: %s",
                format_size(dataframe_memory_bytes),
            )

            end_time = datetime.now()
            final_status = self._build_final_status(
                failed_url_count=failed_url_count,
                output_rows=all_rows,
            )
            status_writer.append(
                build_status_row(
                    data_source=data_source_summary,
                    data_type=data_type,
                    access_method=access_method,
                    status=final_status,
                    status_note=summarize_failure_reasons(
                        failure_reasons=failure_reasons,
                        failed_url_count=failed_url_count,
                    ),
                    start_time=start_time,
                    end_time=end_time,
                    duration_text=format_duration(end_time - start_time),
                    current_download_size=format_size(
                        self.config.output_excel.stat().st_size
                    ),
                    input_count=len(in_df),
                    output_count=len(all_rows),
                    empty_pathogen_old_count=empty_pathogen_old_count,
                    standardized_count=len(all_rows),
                )
            )
            self.logger.info(
                "Runtime status table updated: %s",
                self.config.status_excel,
            )
            return all_rows
        except Exception as exc:
            end_time = datetime.now()
            failure_reasons.append(f"ERROR: {type(exc).__name__}: {exc}")
            status_writer.append(
                build_status_row(
                    data_source=data_source_summary,
                    data_type=data_type,
                    access_method=access_method,
                    status=STATUS_FAILED,
                    status_note=summarize_failure_reasons(
                        failure_reasons=failure_reasons,
                        failed_url_count=max(failed_url_count, 1),
                    ),
                    start_time=start_time,
                    end_time=end_time,
                    duration_text=format_duration(end_time - start_time),
                    current_download_size=(
                        format_size(self.config.output_excel.stat().st_size)
                        if self.config.output_excel.exists()
                        else ""
                    ),
                    input_count=len(in_df),
                    output_count=len(all_rows),
                    empty_pathogen_old_count=self._count_empty_pathogen_old(
                        all_rows
                    ),
                    standardized_count=len(all_rows),
                )
            )
            self.logger.info(
                "Runtime status table updated with failure: %s",
                self.config.status_excel,
            )
            raise

    def _process_single(
        self,
        data_source: str,
        source_url: str,
    ) -> List[Dict[str, str]]:
        article = self.fetcher.fetch(source_url)

        if not article.main_text and not article.table_text:
            self.logger.warning(
                "No usable content extracted from: %s",
                source_url,
            )
            return [
                build_empty_result(
                    data_source,
                    source_url,
                    reason="No article body/table content extracted.",
                )
            ]

        user_prompt = build_user_prompt(
            data_source=data_source,
            source_url=source_url,
            title=article.title,
            main_text=article.main_text,
            table_text=article.table_text,
        )

        raw_content = self._call_llm_with_retry(user_prompt=user_prompt)
        records = parse_llm_records(raw_content)

        if not records:
            self.logger.warning(
                "No structured records returned by LLM: %s",
                source_url,
            )
            return [
                build_empty_result(
                    data_source,
                    source_url,
                    reason="LLM returned no parseable records.",
                )
            ]

        for record in records:
            record["data_source"] = data_source
            record["source_url"] = source_url

        self.logger.info(
            "Extracted %s records from URL: %s",
            len(records),
            source_url,
        )
        return records

    def _call_llm_with_retry(self, user_prompt: str) -> str:
        last_exc = None
        attempts = self.config.max_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                return self.llm_client.chat_completion(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
            except Exception as exc:
                last_exc = exc
                self.logger.warning(
                    "LLM call failed (attempt %s/%s): %s",
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(1.5 * attempt)

        raise RuntimeError(f"LLM call failed after retries: {last_exc}")

    def _count_empty_pathogen_old(self, rows: List[Dict[str, str]]) -> int:
        empty_count = 0
        for row in rows:
            value = row.get("pathogen_old", "")
            if value is None or not str(value).strip():
                empty_count += 1
        return empty_count

    def _extract_failure_reason(self, rows: List[Dict[str, str]]) -> str:
        if len(rows) != 1:
            return ""

        row = rows[0]
        if not self._is_empty_result_row(row):
            return ""

        return str(row.get("original text", "")).strip()

    def _is_empty_result_row(self, row: Dict[str, str]) -> bool:
        for key, value in row.items():
            if key in {"data_source", "source_url", "original text"}:
                continue
            if value is not None and str(value).strip():
                return False
        return True

    def _build_final_status(
        self,
        failed_url_count: int,
        output_rows: List[Dict[str, str]],
    ) -> str:
        if failed_url_count <= 0:
            return STATUS_SUCCEEDED

        non_empty_rows = 0
        for row in output_rows:
            if not self._is_empty_result_row(row):
                non_empty_rows += 1

        if non_empty_rows > 0:
            return STATUS_PARTIAL
        return STATUS_FAILED
