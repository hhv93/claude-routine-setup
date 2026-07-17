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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
