"""Utilities to export ranked topics to CSV or JSON."""
from __future__ import annotations

import io
import json
from typing import List

import pandas as pd

EXPORT_COLUMNS = ["Topic", "Mentions", "Source", "Trend_Score", "Date"]


def dataframe_to_csv(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.StringIO()
    export_df = df.copy()
    if export_df.empty:
        export_df = pd.DataFrame(columns=EXPORT_COLUMNS)
    export_df = export_df.reindex(columns=EXPORT_COLUMNS, fill_value="")
    export_df.to_csv(buffer, index=False)
    byte_buffer = io.BytesIO(buffer.getvalue().encode("utf-8"))
    byte_buffer.seek(0)
    return byte_buffer


def dataframe_to_json(df: pd.DataFrame) -> io.BytesIO:
    records: List[dict] = []
    if not df.empty:
        for _, row in df.iterrows():
            record = {col: row.get(col) for col in EXPORT_COLUMNS}
            record["Trend_Score"] = float(row.get("Trend_Score", 0))
            record["details"] = row.get("details", [])
            records.append(record)
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    byte_buffer = io.BytesIO(payload.encode("utf-8"))
    byte_buffer.seek(0)
    return byte_buffer
