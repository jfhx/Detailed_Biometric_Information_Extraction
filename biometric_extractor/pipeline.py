import time
from typing import Dict, List

from biometric_extractor.config import PipelineConfig
from biometric_extractor.fetcher import ArticleFetcher
from biometric_extractor.io_utils import read_input_rows, save_output
from biometric_extractor.llm_client import LLMClient
from biometric_extractor.logging_utils import setup_logger
from biometric_extractor.postprocess import build_empty_result, parse_llm_records
from biometric_extractor.prompts import SYSTEM_PROMPT, build_user_prompt


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
        in_df = read_input_rows(self.config.input_excel)
        if self.config.limit > 0:
            in_df = in_df.head(self.config.limit).copy()
        self.logger.info("Input rows loaded: %s", len(in_df))

        all_rows: List[Dict[str, str]] = []

        for idx, row in in_df.iterrows():
            data_source = row["data_source"]
            source_url = row["source_url"]
            self.logger.info("[%s/%s] Processing: %s", idx + 1, len(in_df), source_url)

            try:
                records = self._process_single(data_source, source_url)
            except Exception as exc:
                self.logger.exception("Failed to process URL: %s | error=%s", source_url, exc)
                records = [
                    build_empty_result(
                        data_source,
                        source_url,
                        reason=f"ERROR: {type(exc).__name__}: {exc}",
                    )
                ]

            all_rows.extend(records)
            time.sleep(self.config.request_interval_seconds)

        save_output(all_rows, self.config.output_excel, self.config.output_csv)
        self.logger.info("Pipeline completed. Output rows: %s", len(all_rows))
        self.logger.info("Excel output: %s", self.config.output_excel)
        self.logger.info("CSV output: %s", self.config.output_csv)

        return all_rows

    def _process_single(self, data_source: str, source_url: str) -> List[Dict[str, str]]:
        article = self.fetcher.fetch(source_url)

        if not article.main_text and not article.table_text:
            self.logger.warning("No usable content extracted from: %s", source_url)
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
            self.logger.warning("No structured records returned by LLM: %s", source_url)
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

        self.logger.info("Extracted %s records from URL: %s", len(records), source_url)
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
