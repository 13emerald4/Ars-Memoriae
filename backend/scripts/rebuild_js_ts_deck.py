"""Replace "JavaScript & TypeScript: Zero to Mastery" with the coding-first course.

Keeps the root deck and replaces everything under it with the cards in
app/content/js_ts_course (105 cards: write/fix/type code, predict the output,
does it compile). Refuses if any of the old cards has been reviewed, unless
you pass --force. Backs up a SQLite database first.

Usage (from the backend folder, with the app closed):
    .venv\\Scripts\\python.exe scripts\\rebuild_js_ts_deck.py --dry-run
    .venv\\Scripts\\python.exe scripts\\rebuild_js_ts_deck.py
    .venv\\Scripts\\python.exe scripts\\rebuild_js_ts_deck.py --email you@example.com
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from sqlalchemy import select  # noqa: E402

from app.content.js_ts_course import ROOT_NAME  # noqa: E402
from app.content.js_ts_course.install import ReviewHistoryExists, install_course  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def backup_sqlite() -> Path | None:
    url = settings.database_url
    if not url.startswith("sqlite"):
        print("Not SQLite: no file backup made. Back up your database first.")
        return None
    db_path = Path(url.split("///", 1)[1])
    if not db_path.exists():
        return None
    target = db_path.with_name(f"{db_path.name}.bak-js-ts-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(db_path, target)
    return target


async def main(args: argparse.Namespace) -> int:
    async with SessionLocal() as db:
        if args.email:
            user = await db.scalar(select(User).where(User.email == args.email))
            if user is None:
                print(f"No account with email {args.email}.")
                return 1
        else:
            users = (await db.scalars(select(User))).all()
            if len(users) != 1:
                print(f"{len(users)} accounts in this database; pick one with --email:")
                for u in users:
                    print(f"  {u.email}")
                return 1
            user = users[0]

        if not args.dry_run:
            backup = backup_sqlite()
            if backup:
                print(f"Backed up the database to {backup}")

        try:
            report = await install_course(db, user, force=args.force)
        except ReviewHistoryExists as exc:
            await db.rollback()
            print(exc)
            return 2

        if args.dry_run:
            await db.rollback()
            print("Dry run: nothing was changed.")
        else:
            await db.commit()

        verb = "Would replace" if args.dry_run else "Replaced"
        if report.root_created:
            print(f"Created '{ROOT_NAME}'.")
        else:
            print(
                f"{verb} {report.removed_cards} cards in {report.removed_decks} subdecks of '{ROOT_NAME}'."
            )
        print(
            f"{'Would add' if args.dry_run else 'Added'} {report.cards_created} cards in "
            f"{report.decks_created} decks ({report.citations_created} with a documentation quote)."
        )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--email", help="account to install the course for (needed if there are several)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="show what would change, change nothing"
    )
    parser.add_argument(
        "--force", action="store_true", help="replace the deck even though cards have reviews"
    )
    sys.exit(asyncio.run(main(parser.parse_args())))
