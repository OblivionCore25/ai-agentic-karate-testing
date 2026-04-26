import logging
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("karate_ai")


@dataclass
class DataFileSummary:
    """Summary of a CSV or Excel test data file."""
    filename: str
    file_type: str              # "csv" or "excel"
    columns: List[Dict[str, str]]  # [{"name": "col1", "type": "str"}, ...]
    row_count: int
    sample_rows: List[Dict[str, Any]]  # First N rows as dicts


def _infer_type(series) -> str:
    """Infer a human-readable type from a pandas Series."""
    import pandas as pd
    dtype = series.dtype
    if pd.api.types.is_integer_dtype(dtype):
        return "int"
    elif pd.api.types.is_float_dtype(dtype):
        return "float"
    elif pd.api.types.is_bool_dtype(dtype):
        return "bool"
    else:
        return "str"


def read_csv(file_path: str, sample_rows: int = 5) -> Optional[DataFileSummary]:
    """Read a CSV file and return a summary with schema and sample data."""
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        
        columns = [
            {"name": col, "type": _infer_type(df[col])}
            for col in df.columns
        ]
        
        samples = df.head(sample_rows).to_dict(orient="records")
        
        return DataFileSummary(
            filename=os.path.basename(file_path),
            file_type="csv",
            columns=columns,
            row_count=len(df),
            sample_rows=samples
        )
    except Exception as e:
        logger.warning(f"Failed to read CSV file {file_path}: {e}")
        return None


def read_excel(file_path: str, sample_rows: int = 5) -> Optional[DataFileSummary]:
    """Read an Excel file (first sheet) and return a summary with schema and sample data."""
    try:
        import pandas as pd
        df = pd.read_excel(file_path, engine="openpyxl")
        
        columns = [
            {"name": col, "type": _infer_type(df[col])}
            for col in df.columns
        ]
        
        samples = df.head(sample_rows).to_dict(orient="records")
        
        return DataFileSummary(
            filename=os.path.basename(file_path),
            file_type="excel",
            columns=columns,
            row_count=len(df),
            sample_rows=samples
        )
    except Exception as e:
        logger.warning(f"Failed to read Excel file {file_path}: {e}")
        return None


def read_data_file(file_path: str) -> Optional[DataFileSummary]:
    """Read a CSV or Excel file based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        return read_excel(file_path)
    else:
        logger.warning(f"Unsupported data file type: {ext} for {file_path}")
        return None


def format_data_summary(summary: DataFileSummary) -> str:
    """Format a DataFileSummary into a human-readable text block for embedding."""
    lines = []
    lines.append(f"Data Source: {summary.filename} ({summary.file_type})")
    
    col_descriptions = [f"{c['name']} ({c['type']})" for c in summary.columns]
    lines.append(f"Data Schema: {', '.join(col_descriptions)}")
    lines.append(f"Total Rows: {summary.row_count}")
    
    if summary.sample_rows:
        lines.append("Sample Data:")
        for row in summary.sample_rows:
            values = [str(v) for v in row.values()]
            lines.append(f"  {', '.join(values)}")
    
    return "\n".join(lines)
