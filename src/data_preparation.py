"""
Data preparation validation module for PartnerLens Copilot.

For the baseline submission, processed files are included in data/processed/.
This script validates that required processed files are present and readable.
"""

from pathlib import Path
import pandas as pd


PROCESSED_DIR = Path("data/processed")

REQUIRED_PROCESSED_FILES = [
    "partner_master_clean.csv",
    "partner_pricing_clean.csv",
    "partner_metrics_clean.csv",
    "partner_current_preview_1000.csv",
    "phase3_validation_summary.csv",
]


def validate_file_exists(file_name: str) -> Path:
    """Confirm that a processed file exists."""
    file_path = PROCESSED_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Missing required processed file: {file_path}")

    return file_path


def preview_file(file_path: Path) -> None:
    """Print basic file information."""
    df = pd.read_csv(file_path)
    print(f"{file_path.name}: {len(df)} rows, {len(df.columns)} columns")


def main() -> None:
    """Validate processed files for baseline reproducibility."""
    for file_name in REQUIRED_PROCESSED_FILES:
        file_path = validate_file_exists(file_name)
        preview_file(file_path)

    print("All required processed files are present and readable.")


if __name__ == "__main__":
    main()
