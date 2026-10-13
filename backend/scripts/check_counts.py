import sqlite3

conn = sqlite3.connect("dev.db")
c = conn.cursor()
c.execute("SELECT name, (SELECT COUNT(*) FROM cards WHERE cards.deck_id = decks.id) FROM decks WHERE name LIKE '%08%' OR name LIKE '%09%'")
for row in c.fetchall():
    print(f"Deck: {row[0]} -> {row[1]} cards")

c.execute("SELECT COUNT(*) FROM cards")
print(f"Total cards in dev.db: {c.fetchone()[0]}")
conn.close()
