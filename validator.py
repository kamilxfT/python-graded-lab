"""Row validation for the flight query tool."""

import math
import re
from datetime import datetime

FIELD_NAMES = [
    "flight_id",
    "origin",
    "destination",
    "departure_datetime",
    "arrival_datetime",
    "price",
]

# [0-9] and [A-Z] are used on purpose: \d and str.isupper() also accept non-ASCII characters.
FLIGHT_ID_RE = re.compile(r"^[A-Za-z0-9]{2,8}$")
AIRPORT_RE = re.compile(r"^[A-Z]{3}$")
DATETIME_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$")
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def load_airports(path: str) -> set[str]:
    """Read an airport list file and return the set of codes."""
    airports = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            code = line.strip()
            if code == "" or code.startswith("#"):
                continue
            airports.add(code)
    return airports


def parse_datetime(text: str):
    """Return a datetime if text is exactly YYYY-MM-DD HH:MM and a real date, else None."""
    if not DATETIME_RE.match(text):
        return None
    try:
        return datetime.strptime(text, DATETIME_FORMAT)
    except ValueError:
        return None


def validate_row(fields: list[str], airports: set[str]) -> str | None:
    """Return None for a valid row, otherwise the code of the first failing check."""
    # 1. exactly 6 fields
    if len(fields) != 6:
        return "WRONG_FIELD_COUNT"

    flight_id, origin, destination, dep_text, arr_text, price_text = [
        field.strip() for field in fields
    ]

    # 2. no empty field
    if "" in (flight_id, origin, destination, dep_text, arr_text, price_text):
        return "MISSING_FIELD"

    # 3. flight id
    if not FLIGHT_ID_RE.match(flight_id):
        return "INVALID_FLIGHT_ID"

    # 4-5. airports
    if not AIRPORT_RE.match(origin) or origin not in airports:
        return "INVALID_ORIGIN"
    if not AIRPORT_RE.match(destination) or destination not in airports:
        return "INVALID_DESTINATION"

    # 6. same airport
    if origin == destination:
        return "SAME_ORIGIN_DESTINATION"

    # 7-8. date and time
    departure = parse_datetime(dep_text)
    if departure is None:
        return "INVALID_DEPARTURE"
    arrival = parse_datetime(arr_text)
    if arrival is None:
        return "INVALID_ARRIVAL"

    # 9. arrival after departure
    if arrival <= departure:
        return "ARRIVAL_NOT_AFTER_DEPARTURE"

    # 10. price is a finite number
    try:
        price = float(price_text)
    except ValueError:
        return "INVALID_PRICE"
    if not math.isfinite(price):
        return "INVALID_PRICE"

    # 11. price is positive
    if price <= 0:
        return "NON_POSITIVE_PRICE"

    return None


def to_record(fields: list[str]) -> dict:
    """Turn a valid row into a flight record dictionary."""
    values = [field.strip() for field in fields]
    record = dict(zip(FIELD_NAMES, values))
    record["price"] = float(record["price"])
    return record