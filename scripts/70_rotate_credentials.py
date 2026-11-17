"""Rotate local account passwords (R-05, SEC-2).

Earlier versions of Aegis seeded accounts with passwords published in the source
(ChangeMe*). Any database created by those versions still contains them, and with auth
enabled the API refuses to start until they are rotated.

Usage (run from the repository root; uses IDS_DB_URL / IDS_DB_PATH like the API):

    python scripts/70_rotate_credentials.py --check
        list active accounts that still accept a published default password

    python scripts/70_rotate_credentials.py --legacy
        give every such account a new random password, printed ONCE to this terminal

    python scripts/70_rotate_credentials.py --user admin
        set a password for one account; prompts twice (input hidden)

New passwords are printed only to the terminal that runs this script and are never logged.
"""
from __future__ import annotations

import argparse
import getpass
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db import init_db  # noqa: E402
from security.auth.users import user_store  # noqa: E402

MIN_LENGTH = 12


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="list accounts with a published default password")
    g.add_argument("--legacy", action="store_true", help="rotate every account with a published default password")
    g.add_argument("--user", help="set the password of one account (interactive prompt)")
    args = ap.parse_args(argv)

    init_db()
    legacy = user_store.users_with_legacy_passwords()

    if args.check:
        print("accounts with a published default password:", ", ".join(legacy) if legacy else "none")
        return 1 if legacy else 0

    if args.legacy:
        if not legacy:
            print("no account uses a published default password; nothing to rotate")
            return 0
        print("New passwords (shown once; store them in a password manager):")
        for username in legacy:
            pw = secrets.token_urlsafe(18)
            user_store.set_password(username, pw)
            print(f"  {username}: {pw}")
        return 0

    pw = getpass.getpass(f"New password for {args.user}: ")
    if len(pw) < MIN_LENGTH:
        print(f"password must be at least {MIN_LENGTH} characters", file=sys.stderr)
        return 2
    if pw != getpass.getpass("Repeat: "):
        print("passwords do not match", file=sys.stderr)
        return 2
    if not user_store.set_password(args.user, pw):
        print(f"no such user: {args.user}", file=sys.stderr)
        return 2
    print(f"password updated for {args.user}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
