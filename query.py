"""Runs queries against the flight database."""

from validator import FIELD_NAMES, parse_datetime

STRING_KEYS = {"flight_id", "origin", "destination"}
DATETIME_KEYS = {"departure_datetime", "arrival_datetime"}
NUMBER_KEYS = {"price", "min_price"}
ALLOWED_KEYS = STRING_KEYS | DATETIME_KEYS | NUMBER_KEYS | {"sort_by", "order", "limit"}


def is_number(value) -> bool:
    # bool is a subclass of int in Python, but booleans are not numbers here
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_valid_query(query) -> bool:
    if not isinstance(query, dict):
        return False
    for key, value in query.items():
        if key not in ALLOWED_KEYS:
            return False
        if key in STRING_KEYS and not isinstance(value, str):
            return False
        if key in DATETIME_KEYS:
            if not isinstance(value, str) or parse_datetime(value) is None:
                return False
        if key in NUMBER_KEYS and not is_number(value):
            return False
        if key == "sort_by" and value not in FIELD_NAMES:
            return False
        if key == "order" and value not in ("asc", "desc"):
            return False
        if key == "limit":
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return False
    if "order" in query and "sort_by" not in query:
        return False
    return True


def matches(flight: dict, query: dict) -> bool:
    """True if the flight passes every condition in the query (AND)."""
    for key in STRING_KEYS:
        if key in query and flight[key] != query[key]:
            return False
    # "YYYY-MM-DD HH:MM" strings sort in time order, so they can be compared directly
    if "departure_datetime" in query and flight["departure_datetime"] < query["departure_datetime"]:
        return False
    if "arrival_datetime" in query and flight["arrival_datetime"] > query["arrival_datetime"]:
        return False
    if "price" in query and flight["price"] > query["price"]:
        return False
    if "min_price" in query and flight["price"] < query["min_price"]:
        return False
    return True


def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object."""
    if not is_valid_query(query):
        return {"query": query, "error": "INVALID_QUERY", "matches": []}

    result = [flight for flight in db if matches(flight, query)]

    if "sort_by" in query:
        key = query["sort_by"]
        reverse = query.get("order", "asc") == "desc"
        result = sorted(result, key=lambda flight: flight[key], reverse=reverse)

    if "limit" in query:
        result = result[: query["limit"]]

    return {"query": query, "matches": result}


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if isinstance(queries, dict):
        queries = [queries]
    return [run_query(db, query) for query in queries]