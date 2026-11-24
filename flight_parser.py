"""Flight query tool: entry point."""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

STUDENT_ID = "251ADB067"
FIRST_NAME = "Kamil"
LAST_NAME = "Guluzada"


class RuntimeProblem(Exception):
    """An expected problem that ends the program with exit code 1."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate flight CSV files and query them.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-i", metavar="FILE", help="parse a single CSV file")
    source.add_argument("-d", metavar="FOLDER", help="parse every .csv file in a folder")
    source.add_argument("-j", metavar="FILE", help="load an existing JSON database")
    parser.add_argument("-a", metavar="FILE", help="airport list file (required with -i/-d)")
    parser.add_argument("-o", metavar="FILE", help="output JSON database (default: db.json)")
    parser.add_argument("-q", metavar="FILE", help="JSON file with queries")
    parser.add_argument("-r", metavar="FOLDER", default=".", help="folder for the response file")
    return parser


def load_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise RuntimeProblem(f"cannot read {path}: {e.strerror}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeProblem(f"{path} is not valid JSON")


def csv_paths(args) -> list[str]:
    if args.i:
        if not os.path.isfile(args.i):
            raise RuntimeProblem(f"file not found: {args.i}")
        return [args.i]
    if not os.path.isdir(args.d):
        raise RuntimeProblem(f"folder not found: {args.d}")
    names = sorted(
        name for name in os.listdir(args.d)
        if name.endswith(".csv") and os.path.isfile(os.path.join(args.d, name))
    )
    if not names:
        raise RuntimeProblem(f"no .csv files in {args.d}")
    return [os.path.join(args.d, name) for name in names]


def write_errors_log(log_path: str, errors: list[str]) -> None:
    logger = logging.getLogger("flight_parser")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    try:
        for message in errors:
            logger.warning(message)
    finally:
        logger.removeHandler(handler)
        handler.close()


def write_json(path: str, data) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise RuntimeProblem(f"cannot write {path}: {e.strerror}")


def run(args) -> int:
    if args.j:
        db = load_json(args.j)
        if not isinstance(db, list) or not all(isinstance(r, dict) for r in db):
            raise RuntimeProblem(f"{args.j} must contain a JSON array of objects")
    else:
        paths = csv_paths(args)
        try:
            airports = load_airports(args.a)
        except OSError as e:
            raise RuntimeProblem(f"cannot read airport file {args.a}: {e.strerror}")
        except UnicodeDecodeError:
            raise RuntimeProblem(f"cannot read airport file {args.a}")
        try:
            db, errors = parse_files(paths, airports)
        except OSError as e:
            raise RuntimeProblem(f"cannot read CSV file: {e.strerror}")
        except UnicodeDecodeError:
            raise RuntimeProblem("a CSV file is not valid UTF-8")

        out_path = args.o or "db.json"
        write_json(out_path, db)
        log_path = os.path.join(os.path.dirname(os.path.abspath(out_path)), "errors.log")
        try:
            write_errors_log(log_path, errors)
        except OSError as e:
            raise RuntimeProblem(f"cannot write {log_path}: {e.strerror}")
        print(f"{len(db)} valid flights, {len(errors)} invalid rows")

    if args.q:
        queries = load_json(args.q)
        if not isinstance(queries, (dict, list)):
            raise RuntimeProblem(f"{args.q} must contain a query object or an array of them")
        if isinstance(queries, list) and not all(isinstance(q, dict) for q in queries):
            raise RuntimeProblem(f"{args.q} must contain only query objects")
        responses = run_queries(db, queries)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        name = f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{stamp}.json"
        write_json(os.path.join(args.r, name), responses)
        print(f"{len(responses)} queries answered, results in {name}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if (args.i or args.d) and not args.a:
            parser.error("-a is required with -i or -d")
        if args.j and args.o:
            parser.error("-o cannot be used with -j")
    except SystemExit as e:
        # argparse exits with 2 on usage errors and 0 for -h
        return e.code if isinstance(e.code, int) else 2

    try:
        return run(args)
    except RuntimeProblem as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())