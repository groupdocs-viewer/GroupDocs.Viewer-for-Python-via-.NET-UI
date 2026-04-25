"""Sync the vendored Angular SPA from GroupDocs.Viewer-for-.NET-UI.

Default source is a sibling clone at ``../GroupDocs.Viewer-for-.NET-UI``.
Run after pulling a new .NET UI release to update the vendored frontend.

Usage:
    python scripts/sync_frontend.py
    python scripts/sync_frontend.py --source /path/to/GroupDocs.Viewer-for-.NET-UI
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT.parent / "GroupDocs.Viewer-for-.NET-UI"
APP_SUBPATH = Path("src/GroupDocs.Viewer.UI/App")
DEST = ROOT / "src" / "groupdocs_viewer_ui" / "frontend"
VERSION_FILE = DEST.parent / "FRONTEND_VERSION"


def _git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to the GroupDocs.Viewer-for-.NET-UI repo",
    )
    args = parser.parse_args()

    src_app = args.source / APP_SUBPATH
    if not src_app.is_dir():
        print(f"error: {src_app} does not exist", file=sys.stderr)
        return 1

    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(src_app, DEST)

    try:
        commit = _git("rev-parse", "HEAD", cwd=args.source)
        describe = _git("describe", "--tags", "--always", cwd=args.source)
        commit_date = _git("log", "-1", "--format=%ad", "--date=short", cwd=args.source)
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = describe = commit_date = "unknown"

    VERSION_FILE.write_text(
        "source: https://github.com/groupdocs-viewer/GroupDocs.Viewer-for-.NET-UI\n"
        f"commit: {commit}\n"
        f"tag: {describe}\n"
        f"date: {commit_date}\n"
        f"synced: {date.today()}\n",
        encoding="utf-8",
    )

    count = sum(1 for p in DEST.rglob("*") if p.is_file())
    print(f"vendored {count} files from {src_app}")
    print(f"version: {describe} ({commit[:8]}) dated {commit_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
