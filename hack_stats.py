from collections import defaultdict
from requests import cached_request
from abr import ABR
from nrdb import NRDB

cardpool = 'tai'

abr = ABR()
abr.get_tournaments_api('tai') # force a get from API
# TODO fix cardpool in DB
tournaments = abr.get_tournaments('The Automata Initiative', 'standard') # from DB

ids_played = defaultdict(int)
ids_wins = defaultdict(int)
cards_played = defaultdict(int)
cards_wins = defaultdict(int)
 
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


nrdb = NRDB()
print("*** Used IDs")
for id in sorted(ids_played, key = lambda id: ids_played[id], reverse = True):
    name = nrdb.get_card(id).name
    win_rate = int(ids_wins[id] * 100 / ids_played[id])
    print(f'{name} {ids_played[id]} ({win_rate}%)')

print("*** Check pack and cycle usage")
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

print("*** RESULTS ***")
sorted_cycles = sorted(cycles.keys(), key=lambda k: len(cycles[k]) / cycles_size[k], reverse=True)
for code in sorted_cycles:
    cycle_cards = cycles[code]
    print(f"{code} {len(cycle_cards)}/{cycles_size[code]}")
    #cards = list(map(lambda name: (name, cycle_cards[name]), cycle_cards))
    #cards.sort(reverse = True, key = lambda x: x[1])
    #for (name, count) in cards:
    #    print(f'{name},{count}')

used_ice = defaultdict(int)
ice_keywords = defaultdict(int)
for id in cards_played: 
    card = nrdb.get_card(id)
    if card.type == 'ice':
        used_ice[id] += cards_played[id]
        keywords = card.keywords.split(" - ")
        for k in keywords:
            ice_keywords[k] += cards_played[id]

for id in sorted(used_ice.keys(), key=lambda k: used_ice[k], reverse=True):
    card = nrdb.get_card(id)
    print(f'{card.name},{card.keywords},{used_ice[id]}')
for k in sorted(ice_keywords.keys(), key=lambda k: ice_keywords[k], reverse=True):
    print(f'{k},{ice_keywords[k]}')


