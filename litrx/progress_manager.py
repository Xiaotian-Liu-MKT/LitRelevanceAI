"""Progress management for long-running analysis tasks.

This module provides atomic checkpoint saving and recovery to prevent
data loss during program crashes or interruptions.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


class ProgressManager:
    """Manages progress checkpoints for analysis tasks with atomic saves."""

    def __init__(self, output_path: str):
        """Initialize progress manager.

        Args:
            output_path: Base output path for results (CSV or Excel)
        """
        self.output_path = Path(output_path)
        self.checkpoint_dir = self.output_path.parent / ".litrx_checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Generate checkpoint file names based on output file
        base_name = self.output_path.stem
        self.checkpoint_csv = self.checkpoint_dir / f"{base_name}.checkpoint.csv"
        self.checkpoint_json = self.checkpoint_dir / f"{base_name}.checkpoint.json"

    def save_checkpoint(
        self,
        df: pd.DataFrame,
        last_index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save progress checkpoint atomically.

        Uses atomic file replacement to prevent corruption during save.

        Args:
            df: DataFrame with current results
            last_index: Index of last processed row
            metadata: Additional metadata to save (e.g., configuration, timestamp)
        """
        # Prepare metadata
        checkpoint_data = {
            "last_index": last_index,
            "timestamp": datetime.now().isoformat(),
            "total_rows": len(df),
            **(metadata or {})
        }

        # Create temporary files
        temp_csv = self.checkpoint_csv.with_suffix(".tmp.csv")
        temp_json = self.checkpoint_json.with_suffix(".tmp.json")

        try:
            # Save DataFrame to temporary CSV
            if self.output_path.suffix.lower() == '.csv':
                df.to_csv(temp_csv, index=False, encoding='utf-8-sig')
            else:  # Excel
                df.to_excel(temp_csv.with_suffix('.xlsx'), index=False, engine='openpyxl')
                temp_csv = temp_csv.with_suffix('.xlsx')

            # Save metadata to temporary JSON
            with temp_json.open('w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

            # Atomic rename (overwrites existing checkpoint)
            if os.name == 'nt':  # Windows
                # Windows requires removing destination first
                if self.checkpoint_csv.exists():
                    self.checkpoint_csv.unlink()
                if self.checkpoint_json.exists():
                    self.checkpoint_json.unlink()

            # Use shutil.move for cross-platform atomic operations
            shutil.move(str(temp_csv), str(self.checkpoint_csv))
            shutil.move(str(temp_json), str(self.checkpoint_json))

        except Exception as e:
            # Clean up temporary files on error
            if temp_csv.exists():
                temp_csv.unlink()
            if temp_json.exists():
                temp_json.unlink()
            raise RuntimeError(f"Failed to save checkpoint: {e}") from e

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint metadata if it exists.

        Returns:
            Dictionary with checkpoint metadata, or None if no checkpoint exists
        """
        if not self.checkpoint_json.exists():
            return None

        try:
            with self.checkpoint_json.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load checkpoint metadata: {e}")
            return None

    def load_dataframe(self) -> Optional[pd.DataFrame]:
        """Load checkpoint DataFrame if it exists.

        Returns:
            DataFrame with checkpointed data, or None if no checkpoint exists
        """
        if not self.checkpoint_csv.exists():
            return None

        try:
            if self.checkpoint_csv.suffix.lower() == '.csv':
                return pd.read_csv(self.checkpoint_csv, encoding='utf-8-sig')
            else:  # Excel
                return pd.read_excel(self.checkpoint_csv, engine='openpyxl')
        except Exception as e:
            print(f"Warning: Failed to load checkpoint DataFrame: {e}")
            return None

    def has_checkpoint(self) -> bool:
        """Check if a checkpoint exists.

        Returns:
            True if checkpoint exists, False otherwise
        """
        return self.checkpoint_csv.exists() and self.checkpoint_json.exists()

    def clear_checkpoint(self) -> None:
        """Clear existing checkpoint files.

        Call this after successfully completing a task.
        """
        try:
            if self.checkpoint_csv.exists():
                self.checkpoint_csv.unlink()
            if self.checkpoint_json.exists():
                self.checkpoint_json.unlink()
        except Exception as e:
            print(f"Warning: Failed to clear checkpoint: {e}")

    def get_resume_prompt(self) -> Optional[str]:
        """Get a user-friendly message about available checkpoint.

        Returns:
            String message for user, or None if no checkpoint
        """
        metadata = self.load_checkpoint()
        if not metadata:
            return None

        timestamp = metadata.get('timestamp', 'unknown')
        last_index = metadata.get('last_index', 0)
        total = metadata.get('total_rows', 0)

        return (
            f"Found previous checkpoint from {timestamp}\n"
            f"Completed: {last_index}/{total} rows\n"
            f"Resume from checkpoint?"
        )

    def finalize_results(self, df: pd.DataFrame) -> None:
        """Save final results and clear checkpoint.

        Args:
            df: Final DataFrame to save
        """
        try:
            # Save to final output path
            if self.output_path.suffix.lower() == '.csv':
                df.to_csv(self.output_path, index=False, encoding='utf-8-sig')
            else:  # Excel
                df.to_excel(self.output_path, index=False, engine='openpyxl')

            # Clear checkpoint after successful save
            self.clear_checkpoint()

        except Exception as e:
            raise RuntimeError(f"Failed to save final results: {e}") from e


def create_progress_manager(base_path: str, suffix: str = "_analyzed") -> ProgressManager:
    """Create a progress manager with timestamped output path.

    Args:
        base_path: Original input file path
        suffix: Suffix to add to output filename (default: "_analyzed")

    Returns:
        Configured ProgressManager instance
    """
    base = Path(base_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = base.parent / f"{base.stem}{suffix}_{timestamp}{base.suffix}"

    return ProgressManager(str(output_path))
