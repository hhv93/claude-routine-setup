#!/usr/bin/env python3
"""CLI for reading/writing Google Sheets and finding files in Drive,
authenticated via a service account key from GOOGLE_SA_KEY_B64."""

import argparse
import base64
import json
import os
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _load_credentials():
    b64 = os.environ.get("GOOGLE_SA_KEY_B64")
    if not b64:
        sys.exit("GOOGLE_SA_KEY_B64 is not set")
    key_dict = json.loads(base64.b64decode(b64))
    return service_account.Credentials.from_service_account_info(key_dict, scopes=SCOPES)


def cmd_find_file(args):
    creds = _load_credentials()
    drive = build("drive", "v3", credentials=creds)
    query = f"name = '{args.name}' and '{args.folder_id}' in parents and trashed = false"
    files = drive.files().list(q=query, fields="files(id, name)").execute().get("files", [])
    if not files:
        sys.exit(f"No file named '{args.name}' found in folder {args.folder_id}")
    print(files[0]["id"])


def cmd_read(args):
    creds = _load_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    result = sheets.spreadsheets().values().get(
        spreadsheetId=args.spreadsheet_id, range=args.range
    ).execute()
    print(json.dumps(result.get("values", [])))


def cmd_append(args):
    creds = _load_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    rows = json.loads(args.rows_json)
    sheets.spreadsheets().values().append(
        spreadsheetId=args.spreadsheet_id,
        range=args.range,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()
    print(f"Appended {len(rows)} row(s)")


def cmd_check_new(args):
    creds = _load_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    result = sheets.spreadsheets().values().get(
        spreadsheetId=args.spreadsheet_id, range=args.key_range
    ).execute()
    existing = set()
    for row in result.get("values", []):
        if not row:
            continue
        key = args.join.join(cell.strip().lower() for cell in row)
        if key:
            existing.add(key)

    def normalize(candidate):
        return args.join.join(part.strip().lower() for part in candidate.split(args.join))

    candidates = json.loads(args.candidates_json)
    new_ones = [c for c in candidates if normalize(c) not in existing]
    print(json.dumps(new_ones))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("find-file"); p.add_argument("--name", required=True)
    p.add_argument("--folder-id", required=True); p.set_defaults(func=cmd_find_file)

    p = sub.add_parser("read"); p.add_argument("--spreadsheet-id", required=True)
    p.add_argument("--range", required=True); p.set_defaults(func=cmd_read)

    p = sub.add_parser("append"); p.add_argument("--spreadsheet-id", required=True)
    p.add_argument("--range", required=True)
    p.add_argument("--rows-json", required=True, help='JSON list of rows, e.g. \'[["a","b"]]\'')
    p.set_defaults(func=cmd_append)

    p = sub.add_parser("check-new"); p.add_argument("--spreadsheet-id", required=True)
    p.add_argument("--key-range", required=True,
                    help="Column range holding existing dedup keys, e.g. 'G:G' for a single key column "
                         "or 'B:C' to match on a combination of columns (e.g. Company+Title)")
    p.add_argument("--candidates-json", required=True,
                    help='JSON list of candidate keys. For multi-column key-range, join the same fields '
                         'with --join, e.g. \'["indeed:abc123"]\' or \'["OCBC|Group Data Office"]\'')
    p.add_argument("--join", default="|",
                    help="Separator used to join multiple columns into one key (default '|'). "
                         "Matching is case-insensitive and whitespace-trimmed on both sides.")
    p.set_defaults(func=cmd_check_new)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
