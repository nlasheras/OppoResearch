from collections import defaultdict
from requests import cached_request

cardpool = 'ms'
tournament_list = f'https://alwaysberunning.net/api/tournaments?cardpool={cardpool}&type=4'

tournaments_json = cached_request(tournament_list)

card_ids = defaultdict(int)
corp_ids = defaultdict(int)
runner_ids = defaultdict(int)

tournament_entries = "https://alwaysberunning.net/api/entries?id="
for tournament in tournaments_json:
    tournament_id = tournament['id']
    print(tournament['title'])

    url = tournament_entries + str(tournament_id)

    entries_json = cached_request(url)

    decklist_url = "https://netrunnerdb.com/api/2.0/public/decklist/"
    def fetch_cards(url):
        print(url)
        deck_id = url.split("/")[-1]
        deck_json = cached_request(decklist_url + deck_id, f"decks/{deck_id}")
        deck_cards = deck_json['data'][0]['cards']
        for id in deck_cards.keys():
            card_ids[id] += 1

    for entry in entries_json:
        
        rank_top = entry['rank_top']
        if not rank_top:
            continue

        corp_id = entry['corp_deck_identity_id']
        corp_ids[corp_id] += 1
        corp_id = entry['runner_deck_identity_id']
        runner_ids[corp_id] += 1

        corp_url = entry['corp_deck_url']
        if corp_url:
            fetch_cards(corp_url)

        runner_url = entry['runner_deck_url']
        if runner_url:
            fetch_cards(runner_url)
        


card_url = 'https://netrunnerdb.com/api/2.0/public/card/'

for id in corp_ids:
    card_json = cached_request(card_url + id, f"cards/{id}")
    name = card_json['data'][0]['title']
    print(f'{name} {corp_ids[id]}')
for id in runner_ids:
    card_json = cached_request(card_url + id, f"cards/{id}")
    name = card_json['data'][0]['title']
    print(f'{name} {runner_ids[id]}')

packs = defaultdict(lambda: defaultdict(int))
for id in card_ids: 
    card_json = cached_request(card_url + id, f"cards/{id}")
    pack_code = card_json['data'][0]['pack_code']
    name = card_json['data'][0]['title']
    packs[pack_code][name] += card_ids[id]

cycles = defaultdict(lambda: defaultdict(int))
pack_url = 'https://netrunnerdb.com/api/2.0/public/pack/'
for code in packs:
    pack_json = cached_request(pack_url + code, f"packs/{code}")
    cycle_code = pack_json['data'][0]['cycle_code']
    for name in packs[code]:
        cycles[cycle_code][name] += packs[code][name]

for code in cycles:
    cycle_cards = cycles[code]
    print(f"*******{code} {len(cycle_cards)}")
    cards = list(map(lambda name: (name, cycle_cards[name]), cycle_cards))
    cards.sort(reverse = True, key = lambda x: x[1])
    for (name, count) in cards:
        print(f'{name} {count}')
    print("*******")

    