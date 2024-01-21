from collections import defaultdict
from requests import cached_request
from abr import ABR
from nrdb import NRDB
import csv

cardpool = 'tai'

abr = ABR()
tournaments = abr.get_tournaments('The Automata Initiative', format='standard', start_date='2023-11-21')

ids_played = defaultdict(int)
ids_wins = defaultdict(int)
cards_played = defaultdict(int)
cards_wins = defaultdict(int)
 
print(f'Checking data from {len(tournaments)} tournaments...')
for tournament in tournaments:
    for table in tournament.all_tables():
        def count_deck(id, deck, score):
            ids_played[id.id] += 1
            win = 1 if score > 0 else 0
            ids_wins[id.id] += win
        
            if deck != None:
                for (card, _) in deck.cards:
                    cards_played[card.id] += 1
                    cards_wins[card.id] += win

        count_deck(table.player1.corp_id, table.player1.corp_deck, table.corp_score1)
        count_deck(table.player1.runner_id, table.player1.runner_deck, table.runner_score1)
        count_deck(table.player2.corp_id, table.player2.corp_deck, table.corp_score2)
        count_deck(table.player2.runner_id, table.player2.runner_deck, table.runner_score2)


print("*** Most played IDs")
nrdb = NRDB()
with open('ids.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for (pos, id) in enumerate(sorted(ids_played, key = lambda id: ids_played[id], reverse = True), 0):
        name = nrdb.get_card(id).name
        win_rate = int(ids_wins[id] * 100 / ids_played[id])
        writer.writerow([name, ids_played[id],win_rate])
        if pos < 10:
            print(f"{name}: {ids_played[id]}")

print("*** Higher win-rate IDs")
for (pos, id) in enumerate(sorted(ids_played, key = lambda id: ids_wins[id] / ids_played[id], reverse = True), 0):
    name = nrdb.get_card(id).name
    win_rate = int(ids_wins[id] * 100 / ids_played[id])
    if win_rate > 50:
        print(f"{name}: {ids_wins[id]}/{ids_played[id]} {win_rate}%")

print("*** Pack and cycle usage")
packs = defaultdict(lambda: defaultdict(int))
for id in cards_played: 
    card = nrdb.get_card(id)
    packs[card.pack][card.name] += cards_played[id]

cycles = defaultdict(lambda: defaultdict(int))
cycles_size = defaultdict(int)
pack_url = 'https://netrunnerdb.com/api/2.0/public/pack/'
for code in packs:
    pack_json = cached_request(pack_url + code)
    cycle_code = pack_json['data'][0]['cycle_code']
    pack_size = pack_json['data'][0]['size']
    cycles_size[cycle_code] += pack_size
    for name in packs[code]:
        cycles[cycle_code][name] += packs[code][name]

sorted_cycles = sorted(cycles.keys(), key=lambda k: len(cycles[k]) / cycles_size[k], reverse=True)
for code in sorted_cycles:
    cycle_cards = cycles[code]
    print(f"{code} {len(cycle_cards)}/{cycles_size[code]}")
    if True: #code in ['red-sand', 'kitara', 'reign-and-reverie', 'magnum-opus-reprint']:
        cards = list(map(lambda name: (name, cycle_cards[name]), cycle_cards))
        cards.sort(reverse = True, key = lambda x: x[1])

        with open(code + '.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for (name, count) in cards:
                writer.writerow([name, count])

def print_most_used(type = None, keyword = None, count = 10):
    used = defaultdict(int)
    keywords = defaultdict(int)
    for id in cards_played: 
        card = nrdb.get_card(id)
        card_keywords = card.keywords.split(" - ") if card.keywords else []
        if (type != None and card.type == type) or (keyword != None and keyword in card_keywords):
            used[id] += cards_played[id]
            for k in card_keywords:
                keywords[k] += cards_played[id]

    for (pos,id) in enumerate(sorted(used.keys(), key=lambda k: used[k], reverse=True)):
        card = nrdb.get_card(id)
        if pos < count:
            print(f'{card.name} {card.keywords} ({used[id]})')


print("*** Most used ICE")
print_most_used(type = 'ice')

print("*** Most used Breakers")
print_most_used(keyword = 'Fracter', count=3)
print_most_used(keyword = 'Decoder', count=3)
print_most_used(keyword = 'Killer', count=3)
