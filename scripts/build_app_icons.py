"""Build platform and web icons from the generated square source artwork."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "chd-risk-icon.png"


def main() -> None:
    image = Image.open(SOURCE).convert("RGB")
    image = image.resize((1024, 1024), Image.Resampling.LANCZOS)

    image.save(ROOT / "assets" / "chd-risk-icon.icns", format="ICNS")
    image.save(
        ROOT / "assets" / "chd-risk-icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    image.resize((128, 128), Image.Resampling.LANCZOS).save(ROOT / "ui" / "app-icon.png")


if __name__ == "__main__":
    main()
