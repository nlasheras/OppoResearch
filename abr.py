from requests import cached_request
import sqlite3
import time

class TournamentEntry:
    def __init__(self, parent):
        self.__tournament = parent
        self.rank_swiss = 0
        self.rank_top = 0
        self.corp_id = 0
        self.runner_id = 0
        self.corp_deck = None
        self.runner_deck = None
    
    def __repr__(self):
        return f"ABR.TournamentEntry({self.rank_swiss}, {self.rank_top})"

class Tournament:
    def __init__(self, parent, id, name):
        self.__abr = parent
        self.id = id
        self.name = name

    def __repr__(self):
        return f"ABR.Tournament({self.name},{self.id})"
    
    def get_deck_id_from_url(url):
        if len(url) > 0:
            return int(url[url.rfind("/")+1:])
        return None

    def get_entries_api(self):
        url = f'https://alwaysberunning.net/api/entries?id={self.id}'
        response = cached_request(url)
        
        data = []
        for entry in response:
            rank_top = entry['rank_top'] if entry['rank_top'] else 0
            corp_deck = Tournament.get_deck_id_from_url(entry['corp_deck_url'])
            runner_deck = Tournament.get_deck_id_from_url(entry['runner_deck_url'])
            data.append((int(self.id), entry['rank_swiss'], rank_top, int(entry['corp_deck_identity_id']), corp_deck, int(entry['runner_deck_identity_id']), runner_deck))

        cur = self.__abr.con.cursor()
        cur.execute(f"DELETE FROM tournament_entries WHERE tournament_id = {self.id}")
        cur.executemany("INSERT INTO tournament_entries VALUES (?, ?, ?, ?, ?, ?, ?)", data)
        self.__abr.con.commit()

    def top_cut(self):
        cur = self.__abr.con.cursor()
        res = cur.execute(f"SELECT rank_swiss, rank_top, corp_id, corp_deck, runner_id, runner_deck FROM tournament_entries WHERE tournament_id = {self.id} AND rank_top != 0")
        ret = []
        for (rank_swiss, rank_top, corp_id, corp_deck, runner_id, runner_deck) in res:
            entry = TournamentEntry(self)
            entry.rank_swiss = rank_swiss
            entry.rank_top = rank_top
            entry.corp_id = corp_id
            entry.runner_id = runner_id
            entry.corp_deck = corp_deck
            entry.runner_deck = runner_deck
            ret.append(entry)
        ret.sort(key=lambda entry: entry.rank_top)
        return ret

class ABR:
    def __init__(self):
        self.con = sqlite3.connect("abr.db")
        self.__create_db()
        pass

    def __create_db(self):
        cur = self.con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS tournaments(id, name, format, cardpool, banlist, updated_at)")
        cur.execute("CREATE TABLE IF NOT EXISTS tournament_entries(tournament_id, rank_swiss, rank_top, corp_id, corp_deck, runner_id, runner_deck)")

    def get_tournaments_api(self, cardpool):
        url = f'https://alwaysberunning.net/api/tournaments?cardpool={cardpool}'
        response = cached_request(url)

        data = []
        now = int(time.time())
        for tournament in response:
            entry = {} 
            entry['id'] = tournament['id']
            entry['name'] = tournament['title']
            entry['format'] = tournament['format']
            entry['cardpool'] = tournament['cardpool']
            entry['banlist'] = tournament['mwl']
            data.append((int(entry['id']), entry['name'], entry['format'], entry['cardpool'], entry['banlist'], now))

        cur = self.con.cursor()
        cur.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?)", data)
        self.con.commit()

    def get_tournaments(self, cardpool):
        cur = self.con.cursor()
        res = cur.execute("SELECT id, name, updated_at FROM tournaments WHERE format = 'standard'")
        ret = []
        for (id, name, updated_at) in res:
            ret.append(Tournament(self, id, name))
        return ret


if __name__ == "__main__":
    test = ABR()
    #test.get_tournaments_api('tai')
    #print(test.get_tournaments('tai'))
    cascadia = Tournament(test, 3636, '2023 American Conts - Cascadia PNW')
    #cascadia.get_entries_api()
    print(cascadia.top_cut())