from collections import defaultdict
from requests import cached_request
from abr import ABR
from nrdb import NRDB
import csv
from os import makedirs
from os import path

cardpool = 'rwr'

abr = ABR()
tournaments = abr.get_tournaments('Rebellion Without Rehearsal', format='standard', start_date='2024-12-26')

ids_played = defaultdict(int)
ids_wins = defaultdict(int)
cards_played = defaultdict(int)
cards_wins = defaultdict(int)
 
only_top = True
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

        if only_top == False or table.player1.rank_top:
            count_deck(table.player1.corp_id, table.player1.corp_deck, table.corp_score1)
            count_deck(table.player1.runner_id, table.player1.runner_deck, table.runner_score1)
        if only_top == False or table.player2.rank_top:
            count_deck(table.player2.corp_id, table.player2.corp_deck, table.corp_score2)
            count_deck(table.player2.runner_id, table.player2.runner_deck, table.runner_score2)


print("*** Most played IDs")
nrdb = NRDB()
if not path.exists('output'):
    makedirs('output')
with open('output/ids.csv', 'w', newline='', encoding='utf-8') as csvfile:
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
rotated_cards = []
for code in sorted_cycles:
    cycle_cards = cycles[code]
    print(f"{code} {len(cycle_cards)}/{cycles_size[code]}")
    if code in ['red-sand', 'kitara', 'reign-and-reverie', 'magnum-opus-reprint', 'system-update-2021' ]:
        cards = list(map(lambda name: (name, cycle_cards[name], code), cycle_cards))
        rotated_cards += cards
    if True:
        cards = list(map(lambda name: (name, cycle_cards[name]), cycle_cards))
        cards.sort(reverse = True, key = lambda x: x[1])

        with open('output/' + code + '.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for (name, count) in cards:
                writer.writerow([name, count])

rotated_cards.sort(reverse = True, key = lambda x: x[1])
with open('output/dawn_rotation.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    for (name, count, code) in rotated_cards:
        writer.writerow([name, code, count])

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
#print_most_used(type = 'ice')
print_most_used(keyword = 'Barrier')
print_most_used(keyword = 'Sentry')
print_most_used(keyword = 'Code Gate')

print("*** Most used Breakers")
print_most_used(keyword = 'Fracter', count=3)
print_most_used(keyword = 'Decoder', count=3)
print_most_used(keyword = 'Killer', count=3)
