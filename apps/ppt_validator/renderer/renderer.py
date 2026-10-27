"""Slide renderer — LibreOffice PPT→PNG, with graceful unavailable fallback."""
from __future__ import annotations
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path


class SlideRenderer(ABC):
    @abstractmethod
    def render(self, pptx_path: str, output_dir: str) -> list[str]:
        """Return list of PNG file paths, one per slide."""


class LibreOfficeRenderer(SlideRenderer):
    def render(self, pptx_path: str, output_dir: str) -> list[str]:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "png", "--outdir", output_dir, pptx_path],
            check=True, capture_output=True, timeout=120,
        )
        stem = Path(pptx_path).stem
        return sorted(Path(output_dir).glob(f"{stem}*.png"), key=lambda p: p.name)


class UnavailableRenderer(SlideRenderer):
    def render(self, pptx_path: str, output_dir: str) -> list[str]:
        return []


def get_renderer() -> SlideRenderer:
    if os.getenv("RENDERER", "libreoffice") == "libreoffice":
        try:
            subprocess.run(["libreoffice", "--version"], check=True, capture_output=True)
            return LibreOfficeRenderer()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return UnavailableRenderer()
