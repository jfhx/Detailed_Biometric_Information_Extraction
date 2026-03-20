from pathlib import Path
from typing import List

import pandas as pd

from biometric_extractor.models import OUTPUT_COLUMNS


def read_input_rows(excel_path: Path) -> pd.DataFrame:
    df = pd.read_excel(excel_path)

    required_columns = {"data_source", "source_url"}
    missing = required_columns.difference(set(df.columns))
    if missing:
        raise ValueError(
            f"Input file missing required columns: {sorted(missing)}"
        )

    df = df[["data_source", "source_url"]].copy()
    df["data_source"] = df["data_source"].fillna("").astype(str).str.strip()
    df["source_url"] = df["source_url"].fillna("").astype(str).str.strip()

    df = df[df["source_url"] != ""].reset_index(drop=True)
    return df


def save_output(rows: List[dict], output_excel: Path, output_csv: Path) -> None:
    output_excel.parent.mkdir(parents=True, exist_ok=True)

    out_df = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in out_df.columns:
            out_df[col] = ""

    out_df = out_df[OUTPUT_COLUMNS]

    out_df.to_excel(output_excel, index=False)
    out_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
