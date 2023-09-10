from requests import cached_request
import sqlite3
import json

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
        cur.execute("CREATE TABLE IF NOT EXISTS cards(id, name, type, faction, keywords, pack)")
        cur.execute("CREATE TABLE IF NOT EXISTS decklists(id, name, cards_json)")

    def get_card_api(self, id):
        url = f'https://netrunnerdb.com/api/2.0/public/card/{id:05}'
        response = cached_request(url, f"cards/{id}")

        data = []
        if response:
            card_data = response['data'][0]
            name = card_data['title']
            type = card_data['type_code']
            faction = card_data['faction_code']
            keywords = card_data['keywords'] if 'keywords' in card_data else None
            pack = card_data['pack_code']
            data.append((id, name, type, faction, keywords, pack))

        cur = self.con.cursor()
        cur.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?)", data)
        self.con.commit()
        
        c = Card(id, name)
        c.type = type
        c.faction = faction
        c.keywords = keywords
        return c
    
    def get_card(self, id):
        cur = self.con.cursor()
        res = cur.execute(f"SELECT name, type, faction, keywords, pack FROM cards WHERE id = {id}")
        rows = res.fetchall()
        if rows:
            data = rows[0]
            c = Card(id, data[0])
            c.type = data[1]
            c.faction = data[2]
            c.keywords = data[3]
            c.pack = data[4]
            return c
        return self.get_card_api(id)
    
    def get_decklist_api(self, id):
        url = f"https://netrunnerdb.com/api/2.0/public/decklist/{id}"
        response = cached_request(url, f"decks/{id}")

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


if __name__ == "__main__":
    test = NRDB()
    print(test.get_card(26066))
    print(test.get_decklist(77001))
    print(test.get_decklist(77265))