"""Keep the '! ' prefix on decks in sync with their missing-documents note.

A deck is marked '!' exactly when its documentation contains a "Missing for full coverage:"
block that still lists at least one `[needs: <path>]` item. build_mt3_decks.py writes and
refreshes those blocks (re-run it with --refresh-docs after dropping a new LA or Lab spec into
Cards Documents). Replaces the old hard-coded prefix list, which would have re-marked Ch 08/09
(their LA08/LA09 specs now exist) and stripped the marker from the Midterm 3 decks.
"""

import asyncio
import logging
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Deck, User  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USER_EMAIL = "michael.r.polley@outlook.com"
NEEDS = re.compile(r"\[needs: [^\]]+\]")


def is_missing(documentation: str | None) -> bool:
    doc = documentation or ""
    return "Missing for full coverage:" in doc and bool(NEEDS.search(doc))


async def mark_missing():
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if not user:
            logger.error("User not found")
            return

        decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
        updated_count = 0
        for d in decks:
            bare = d.name.removeprefix("! ")
            wanted = ("! " + bare) if is_missing(d.documentation) else bare
            if d.name != wanted:
                logger.info(f"'{d.name}' -> '{wanted}'")
                d.name = wanted
                updated_count += 1

        await db.commit()
        logger.info(f"Updated {updated_count} deck names.")


if __name__ == "__main__":
    asyncio.run(mark_missing())
