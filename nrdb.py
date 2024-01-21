from requests import cached_request
import sqlite3
import json
import urllib.parse

class Card:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __repr__(self):
        return f"NRDB.Card({self.name})"

class Decklist:
    def __init__(self, list_id, name):
        self.id = list_id
        self.name = name
        self.cards = []

    def __repr__(self):
        return f"NRDB.Deck({self.id, self.card_id.name})"
    
    def load_cards(self, nrdb, cards_json):
        card_data = json.loads(cards_json)
        self.cards = []
        for card_id in card_data.keys():
            card = nrdb.get_card(int(card_id))
            if card.type == 'identity':
                self.card_id = card
            else:
                self.cards += [(card, card_data[card_id])]

   
class NRDB:
    def __init__(self):
        self.con = sqlite3.connect("nrdb.db")
        self.__create_db()
        pass

    def __create_db(self):
        cur = self.con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS cards(id, name, type, faction, keywords, pack, latest_printing)")
        cur.execute("CREATE TABLE IF NOT EXISTS decklists(id, name, cards_json)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cards ON cards(id)")

    def get_card_api(self, id):
        url = f'https://netrunnerdb.com/api/2.0/public/card/{id:05}'
        response = cached_request(url)

        data = []
        if response:
            card_data = response['data'][0]
            name = card_data['title']
            type = card_data['type_code']
            faction = card_data['faction_code']
            keywords = card_data['keywords'] if 'keywords' in card_data else None
            pack = card_data['pack_code']
            data.append((id, name, type, faction, keywords, pack, None))

        cur = self.con.cursor()
        cur.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?)", data)
        self.con.commit()
        
        c = Card(id, name)
        c.type = type
        c.faction = faction
        c.keywords = keywords
        return c
    
    def get_card(self, id):
        cur = self.con.cursor()
        res = cur.execute(f"SELECT name, type, faction, keywords, pack, latest_printing FROM cards WHERE id = {id}")
        rows = res.fetchall()
        if rows:
            data = rows[0]
            if data[5]:
                return self.get_card(data[5])
            c = Card(id, data[0])
            c.type = data[1]
            c.faction = data[2]
            c.keywords = data[3]
            c.pack = data[4]
            return c
        return self.get_card_api(id)
    
    def get_decklist_api(self, id):
        url = f"https://netrunnerdb.com/api/2.0/public/decklist/{id}"
        response = cached_request(url)

        data = []
        if response:
            list_data = response['data'][0]
            name = list_data['name']
            cards = list_data['cards']
            cards_json = json.dumps(cards)
            data.append((id, name, cards_json))

        cur = self.con.cursor()
        cur.executemany("INSERT INTO decklists VALUES (?, ?, ?)", data)
        self.con.commit()
        
        d = Decklist(id, name)
        d.load_cards(self, cards_json)
        return d

    def get_decklist(self, id):
        cur = self.con.cursor()
        res = cur.execute(f"SELECT name, cards_json FROM decklists WHERE id = {id}")
        rows = res.fetchall()
        if rows:
            list_data = rows[0]
            d = Decklist(id, list_data[0])
            d.load_cards(self, list_data[1])
            return d
        return self.get_decklist_api(id)

    def fix_cards_api3_old_packs(self, higher_id = 12000):
        cur = self.con.cursor()
        res = cur.execute(f"SELECT id FROM cards WHERE id < {higher_id} AND latest_printing IS NULL")
        ids = []
        for (id,) in res:
            ids.append(id)
        self.___fix_cards_api3(ids)

    def fix_cards_api3_by_name(self, name):
        cur = self.con.cursor()
        res = cur.execute(f"SELECT id FROM cards WHERE name == '{name}' AND latest_printing IS NULL")
        ids = []
        for (id,) in res:
            ids.append(id)
        self.___fix_cards_api3(ids)

    def ___fix_cards_api3(self, card_ids):
        cur = self.con.cursor()
        latests = []
        for id in card_ids:
            old_card = self.get_card(id)
            print(f"Looking for other printings for {old_card.name}")
            card_name_safe = urllib.parse.quote(old_card.name)
            card_search = cached_request(f"https://api-preview.netrunnerdb.com/api/v3/public/cards?filter[search]={card_name_safe}", use_cache = False)
            if card_search:
                api3_id = card_search['data'][0]['id']
                printings_data = cached_request(f"https://api-preview.netrunnerdb.com/api/v3/public/cards/{api3_id}/relationships/printings", use_cache = False)
                if printings_data:
                    printings = []
                    for p in printings_data['data']:
                        printings.append(int(p['id']))
                    latest = max(printings)
                    if latest != id:
                        latests.append((latest, id))
        if latests:
            cur.executemany("UPDATE cards SET latest_printing = ? WHERE id = ?", latests)
            self.con.commit()

if __name__ == "__main__":
    nrdb = NRDB()
    print(nrdb.get_card(26066))
    print(nrdb.get_decklist(77001))
    print(nrdb.get_decklist(77265))
    nrdb.fix_cards_api3_old_packs()
    nrdb.fix_cards_api3_by_name('Hortum')
    nrdb.fix_cards_api3_by_name('Marilyn Campaign')