import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
cards = json.load(open('span321_current_cards.json', encoding='utf-8'))
for idx in [0, 5, 7, 12, 13, 29, 39]:
    c = cards[idx]
    print('='*60)
    print(f"CARD {idx+1} FRONT: {c['front']}")
    print('-'*20)
    print(f"BACK:\n{c['back']}")
