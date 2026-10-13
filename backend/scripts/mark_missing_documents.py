"""Add '!' to trees/decks that are missing documents to make cards (unreleased by instructor)."""

import asyncio
import logging

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Deck, User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USER_EMAIL = "michael.r.polley@outlook.com"

# Decks that are missing documents to make cards (unreleased materials from instructor or missing card docs)
MISSING_DECKS_PREFIXES = [
    "Ch 08: Designing for Failure",
    "Ch 09: Validating Behaviour",
    "Part 2: Abstraction",
    "Ch 10:",
    "Ch 11:",
    "Ch 12:",
    "Ch 13:",
    "Ch 14:",
    "Ch 15:",
    "Ch 16:",
    "Part 3: Evolution",
    "Ch 17:",
    "Ch 18:",
    "Ch 19:",
    "Ch 20:",
    "Ch 21:",
    "Ch 22:",
]

async def mark_missing():
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if not user:
            logger.error("User not found")
            return

        decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
        updated_count = 0

        for d in decks:
            # Check if this deck matches any missing prefix
            matched = False
            for prefix in MISSING_DECKS_PREFIXES:
                if d.name.startswith(prefix) or d.name.startswith(f"! {prefix}"):
                    matched = True
                    break

            if matched:
                if not d.name.startswith("! "):
                    old_name = d.name
                    d.name = f"! {d.name}"
                    logger.info(f"Updated deck: '{old_name}' -> '{d.name}'")
                    updated_count += 1
            else:
                # Ensure decks with complete docs (Ch 1-7, Part 1, Root) don't have '!' prefix
                if d.name.startswith("! "):
                    d.name = d.name[2:]
                    logger.info(f"Cleaned deck name: '{d.name}'")
                    updated_count += 1

        await db.commit()
        logger.info(f"Successfully updated {updated_count} decks with '!' indicator.")

if __name__ == "__main__":
    asyncio.run(mark_missing())
