"""Create a consistent private SQLite backup without overwriting an existing file."""

import argparse
import os
import sqlite3
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error("Source database does not exist")
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with sqlite3.connect(args.source.resolve().as_uri() + "?mode=ro", uri=True) as source:
            with sqlite3.connect(args.destination) as destination:
                source.backup(destination)
    except Exception:
        args.destination.unlink(missing_ok=True)
        raise
    print(f"Backup written to {args.destination}")


if __name__ == "__main__":
    main()
