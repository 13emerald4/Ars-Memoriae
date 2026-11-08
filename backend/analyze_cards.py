import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('span321_current_cards.json', encoding='utf-8') as f:
    cards = json.load(f)

print(f"Total cards: {len(cards)}")
for i, c in enumerate(cards):
    dname = c.get('deck_name', '')
    front = c.get('front', '').replace('\n', ' ')
    back = c.get('back', '')
    has_tree = '├──' in back or '└──' in back or '│' in back
    has_citation = bool(re.search(r'\[(?:Guía|T\d|Intro|Topic)[^\]]+\]', back))
    print(f"[{i+1:02d}] Deck: {dname}")
    print(f"     Front: {front[:90]}")
    print(f"     Has Tree: {has_tree} | Has Citation: {has_citation} | Back Len: {len(back)}")
