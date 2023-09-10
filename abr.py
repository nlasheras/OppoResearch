from requests import cached_request
import sqlite3
import time
from nrdb import NRDB

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
        response = cached_request(url, f"tournament/{self.id}")
        
        if 'warn' in response:
            print(response['warn'])
            return
         
        cur = self.__abr.con.cursor()
        insert = []
        update = []
        for entry in response:
            rank_swiss = entry['rank_swiss']
            rank_top = entry['rank_top'] if entry['rank_top'] else None
            corp_deck = Tournament.get_deck_id_from_url(entry['corp_deck_url'])
            runner_deck = Tournament.get_deck_id_from_url(entry['runner_deck_url'])
            user_name = entry['user_name'] if entry['user_name'] else entry['user_import_name']
            corp_id = int(entry['corp_deck_identity_id'])
            runner_id = int(entry['runner_deck_identity_id'])
            old_data = cur.execute("SELECT user_name, corp_id, corp_deck, runner_id, runner_deck FROM tournament_entries WHERE tournament_id = ? AND rank_swiss = ?", (self.id, rank_swiss)).fetchall()
            if old_data:
                if old_data[0] != (user_name, corp_id, corp_deck, runner_id, runner_deck):
                    update.append((user_name, corp_id, corp_deck, runner_id, runner_deck, int(self.id), rank_swiss))
            else:
                insert.append((int(self.id), rank_swiss, rank_top, user_name, corp_id, corp_deck, runner_id, runner_deck))
        
        if len(insert) > 0:
            cur.executemany("INSERT INTO tournament_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)", insert)
        if len(update) > 0:
            cur.executemany("UPDATE tournament_entries SET user_name = ?, corp_id = ?, corp_deck = ?, runner_id = ?, runner_deck = ? WHERE tournament_id = ? AND rank_swiss = ?", update)
        now = int(time.time())
        cur.execute("UPDATE tournaments SET updated_at = ? WHERE id = ?", (now, self.id))
        self.__abr.con.commit()

    def __entries(self, top_cut_only):
        cur = self.__abr.con.cursor()
        query = f"SELECT rank_swiss, rank_top, corp_id, corp_deck, runner_id, runner_deck FROM tournament_entries WHERE tournament_id = {self.id}"
        if (top_cut_only):
            query += " AND rank_top IS NOT NULL"
        res = cur.execute(query)
        ret = []
        for (rank_swiss, rank_top, corp_id, corp_deck, runner_id, runner_deck) in res:
            entry = TournamentEntry(self)
            entry.rank_swiss = rank_swiss
            entry.rank_top = rank_top
            entry.corp_id = self.__abr.nrdb.get_card(corp_id)
            entry.runner_id = self.__abr.nrdb.get_card(runner_id) 
            entry.corp_deck = self.__abr.nrdb.get_decklist(corp_deck) if corp_deck else None
            entry.runner_deck = self.__abr.nrdb.get_decklist(runner_deck) if runner_deck else None
            ret.append(entry)
        return ret
    
    def top_cut(self):
        ret = self.__entries(True)
        ret.sort(key=lambda entry: entry.rank_top)
        return ret
        
    def all_entries(self):
        ret = self.__entries(False)
        ret.sort(key=lambda entry: entry.rank_swiss)
        return ret

class ABR:
    def __init__(self):
        self.nrdb = NRDB()
        self.con = sqlite3.connect("abr.db")
        self.__create_db()
        pass

    def __create_db(self):
        cur = self.con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS tournaments(id, name, format, cardpool, banlist, updated_at)")
        cur.execute("CREATE TABLE IF NOT EXISTS tournament_entries(tournament_id, rank_swiss, rank_top, user_name, corp_id, corp_deck, runner_id, runner_deck)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tournament_entries ON tournament_entries(tournament_id, rank_swiss)")

    def get_tournaments_api(self, cardpool):
        url = f'https://alwaysberunning.net/api/tournaments?cardpool={cardpool}&limit=100'
        response = cached_request(url)
        
        cur = self.con.cursor()

        insert = []
        now = int(time.time())
        for tournament in response:
            if not tournament['concluded']:
                continue
            tournament_id = int(tournament['id'])
            if cur.execute(f"SELECT id FROM tournaments WHERE id = {tournament_id}").fetchall():
                continue
            insert.append((tournament_id, tournament['title'], tournament['format'], tournament['cardpool'], tournament['mwl'], now))

        cur.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?)", insert)
        self.con.commit()

    def get_tournaments(self, cardpool):
        cur = self.con.cursor()
        res = cur.execute("SELECT id, name, updated_at FROM tournaments WHERE format = 'standard'")
        ret = []
        now = int(time.time())
        ttl = 24 * 3600
        for (id, name, updated_at) in res:
            t = Tournament(self, id, name)
            if now - updated_at > ttl:
                print(f"Updating entries for {name}...")
                t.get_entries_api()
            ret.append(t)
        return ret


if __name__ == "__main__":
    test = ABR()
    #test.get_tournaments_api('tai')
    #print(test.get_tournaments('tai'))
    cascadia = Tournament(test, 3636, '2023 American Conts - Cascadia PNW')
    #cascadia.get_entries_api()
    print(cascadia.top_cut())