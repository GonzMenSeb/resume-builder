"""Pipeline logging infrastructure with per-stage log files and a master log."""

from __future__ import annotations

import logging
from pathlib import Path
from time import monotonic

LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

STAGE_FILE_MAP: dict[str, str] = {
    "loading": "01_loading.log",
    "extraction": "02_extraction.log",
    "optimization": "03_optimization.log",
    "tailoring": "04_tailoring.log",
    "generation": "05_generation.log",
    "compilation": "06_compilation.log",
    "refinement": "07_refinement.log",
}


class PipelineLogging:
    """Manages master and per-stage file handlers for the resume_generator logger."""

    def __init__(self, log_dir: Path, level: str = "INFO") -> None:
        self._log_dir = log_dir
        self._level = getattr(logging, level.upper(), logging.INFO)
        self._root_logger = logging.getLogger("resume_generator")
        self._formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        self._master_handler: logging.FileHandler | None = None
        self._stage_handler: logging.FileHandler | None = None
        self._current_stage: str | None = None
        self._stage_start: float | None = None

    def setup(self) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._root_logger.setLevel(self._level)

        self._master_handler = logging.FileHandler(self._log_dir / "master.log", encoding="utf-8")
        self._master_handler.setLevel(self._level)
        self._master_handler.setFormatter(self._formatter)
        self._root_logger.addHandler(self._master_handler)

    def _log_stage_duration(self) -> None:
        if self._current_stage is not None and self._stage_start is not None:
            elapsed = monotonic() - self._stage_start
            logging.getLogger("resume_generator.pipeline").info(
                "Stage %s completed in %.1fs", self._current_stage.upper(), elapsed
            )

    def enter_stage(self, stage_name: str) -> None:
        self._log_stage_duration()

        if self._stage_handler is not None:
            self._root_logger.removeHandler(self._stage_handler)
            self._stage_handler.close()
            self._stage_handler = None

        filename = STAGE_FILE_MAP.get(stage_name)
        if filename is None:
            return

        self._current_stage = stage_name
        self._stage_start = monotonic()
        self._stage_handler = logging.FileHandler(self._log_dir / filename, encoding="utf-8")
        self._stage_handler.setLevel(self._level)
        self._stage_handler.setFormatter(self._formatter)
        self._root_logger.addHandler(self._stage_handler)

        separator = f"{'=' * 60}"
        logging.getLogger("resume_generator.pipeline").info(
            "%s\n  Stage: %s\n%s", separator, stage_name.upper(), separator
        )

    def teardown(self) -> None:
        self._log_stage_duration()

        if self._stage_handler is not None:
            self._root_logger.removeHandler(self._stage_handler)
            self._stage_handler.close()
            self._stage_handler = None

        if self._master_handler is not None:
            self._root_logger.removeHandler(self._master_handler)
            self._master_handler.close()
            self._master_handler = None

        self._current_stage = None
        self._stage_start = None

    @property
    def log_dir(self) -> Path:
        return self._log_dir
