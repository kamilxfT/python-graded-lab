"""Reads flight CSV files and collects valid records and error messages."""

import csv
import os

from validator import to_record, validate_row


def read_lines(path: str) -> list[str]:
    """Return the physical lines of a UTF-8 file, without \\n or \\r\\n endings."""
    # newline="" so we see the real line endings and can strip \r ourselves
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")

    # a trailing newline leaves an empty string at the end, drop it
    if lines and lines[-1] == "":
        lines.pop()

    return [l.removesuffix("\r") for l in lines]


def parse_files(paths: list[str], airports: set[str]) -> tuple[list[dict], list[str]]:
    """Process the files in order; return (valid records, error messages)."""
    records = []
    errors = []
    # duplicates are checked across all files, by flight id + departure time
    seen = set()

    for path in paths:
        name = os.path.basename(path)
        lines = read_lines(path)

        # first line is always the header
        for n, line in enumerate(lines[1:], start=2):
            if not line.strip() or line.strip().startswith("#"):
                continue

            fields = next(csv.reader([line]), [])
            error = validate_row(fields, airports)

            if error is None:
                rec = to_record(fields)
                key = (rec["flight_id"], rec["departure_datetime"])
                if key in seen:
                    error = "DUPLICATE_FLIGHT"
                else:
                    seen.add(key)
                    records.append(rec)

            if error:
                errors.append(f"{name}:{n}: {error} | {line}")

    return records, errors