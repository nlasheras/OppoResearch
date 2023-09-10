from collections import defaultdict
from requests import cached_request
from abr import ABR
from nrdb import NRDB

cardpool = 'tai'

abr = ABR()
tournaments = abr.get_tournaments('tai') # from DB

card_ids = defaultdict(int)
corp_ids = defaultdict(int)
runner_ids = defaultdict(int)

for tournament in tournaments:
    #print(tournament)
    #tournament.get_entries_api()

    for entry in tournament.all_entries():
        #print(entry)
        corp_ids[entry.corp_id.id] += 1
        runner_ids[entry.runner_id.id] += 1

        def count_cards(deck):
            for pair in deck.cards:
                card_ids[pair[0].id] += 1    
            
        if entry.corp_deck:
            count_cards(entry.corp_deck)
        if entry.runner_deck:
            count_cards(entry.runner_deck)



nrdb = NRDB()
print("*** Used Corp IDs")
for id in sorted(corp_ids, key = lambda id: corp_ids[id], reverse = True):
    name = nrdb.get_card(id).name
    print(f'{name} {corp_ids[id]}')
print("*** Used Runner IDs")
for id in sorted(runner_ids, key = lambda id: runner_ids[id], reverse = True):
    name = nrdb.get_card(id).name
    print(f'{name} {runner_ids[id]}')

print("*** Check pack and cycle usage")
packs = defaultdict(lambda: defaultdict(int))
for id in card_ids: 
    card = nrdb.get_card(id)
    packs[card.pack][card.name] += card_ids[id]

cycles = defaultdict(lambda: defaultdict(int))
cycles_size = defaultdict(int)
pack_url = 'https://netrunnerdb.com/api/2.0/public/pack/'
for code in packs:
    pack_json = cached_request(pack_url + code, f"packs/{code}")
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

    