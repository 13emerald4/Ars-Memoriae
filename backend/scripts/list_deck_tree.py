import sqlite3

conn = sqlite3.connect('backend/dev.db')
c = conn.cursor()
decks = c.execute("SELECT id, parent_id, name, default_priority, position FROM decks WHERE user_id = '3e12b0d72e0e4d878e1b091bdaa3caa2'").fetchall()
by_parent = {}
for d in decks:
    by_parent.setdefault(d[1], []).append(d)

def show(parent_id, indent=0):
    for d in sorted(by_parent.get(parent_id, []), key=lambda x: (x[4] if x[4] is not None else 0, x[2])):
        print('  ' * indent + f"- {d[2]} (id={d[0]}, prio={d[3]}, pos={d[4]})")
        show(d[0], indent + 1)

print("DECK TREE:")
show(None)
