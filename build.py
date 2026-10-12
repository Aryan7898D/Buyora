"""Prepare the frontend as static assets for Vercel's public directory."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "frontend"
PUBLIC = ROOT / "public"


def main():
    shutil.copytree(SOURCE, PUBLIC, dirs_exist_ok=True)
    (PUBLIC / "js" / "config.js").write_text(
        'window.BUYORA_API_BASE = "/api";\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
