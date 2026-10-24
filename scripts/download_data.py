"""Download the consolidated IRVE file (cached) and build the processed parquet.

    python scripts/download_data.py              # download if missing, then process
    python scripts/download_data.py --force      # re-download the latest version
    python scripts/download_data.py --max-age 7  # re-download if the copy is older than 7 days
    python scripts/download_data.py --from-file path/to/irve.csv   # use a file you already have
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.constants import IRVE_CSV_URL, RAW_CSV  # noqa: E402
from utils.io import build_or_load, fetch_and_cache  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default=IRVE_CSV_URL, help="Override the source URL")
    p.add_argument("--force", action="store_true", help="Re-download even if a local copy exists")
    p.add_argument("--max-age", type=int, default=None, help="Re-download if older than N days")
    p.add_argument("--from-file", type=Path, help="Use a local CSV instead of downloading")
    args = p.parse_args()

    t0 = time.time()
    if args.from_file:
        RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.from_file, RAW_CSV)
        from utils.io import RAW_MANIFEST
        RAW_MANIFEST.unlink(missing_ok=True)
        print(f"Copied {args.from_file} → {RAW_CSV}")
    else:
        print(f"Fetching {args.url} …")
        path = fetch_and_cache(args.url, force=args.force, max_age_days=args.max_age)
        print(f"Raw file ready: {path} ({path.stat().st_size / 1e6:.1f} MB)")

    df, report = build_or_load(force=True)
    print(f"Processed {report['raw_rows']:,} raw rows → {report['final_rows']:,} charge points "
          f"in {time.time() - t0:.1f}s")
    for c in report["checks"]:
        if c["rows"]:
            print(f"  · {c['check']:<30} {c['rows']:>8,} rows  → {c['action']}")


if __name__ == "__main__":
    main()
