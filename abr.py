from requests import cached_request
import sqlite3
import time
from nrdb import NRDB

class TournamentEntry:
    def __init__(self, parent):
        self.__tournament = parent
        self.user_name = ""
        self.rank_swiss = 0
        self.rank_top = 0
        self.corp_id = 0
        self.runner_id = 0
        self.corp_deck = None
        self.runner_deck = None
    
    def __repr__(self):
        return f"ABR.TournamentEntry({self.rank_swiss}, {self.rank_top}, {self.user_name})"

class Table:
    def __init__(self, parent):
        self.__tournament = parent
        self.player1 = None
        self.player2 = None
        self.corp_score1 = 0
        self.runner_score1 = 0
        self.corp_score2 = 0
        self.runner_score2 = 0
        self.table_type = None

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
        
        if response is None:
            return
        
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
        query = f"SELECT user_name, rank_swiss, rank_top, corp_id, corp_deck, runner_id, runner_deck FROM tournament_entries WHERE tournament_id = {self.id}"
        if (top_cut_only):
            query += " AND rank_top IS NOT NULL"
        res = cur.execute(query)
        ret = []
        for (user_name, rank_swiss, rank_top, corp_id, corp_deck, runner_id, runner_deck) in res:
            entry = TournamentEntry(self)
            entry.user_name = user_name
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

    def all_tables(self):
        cur = self.__abr.con.cursor()
        query = f"SELECT round, table_idx, rank_swiss1, corp_score1, runner_score1, rank_swiss2, corp_score2, runner_score2, table_type FROM tournament_tables WHERE tournament_id = {self.id}"
        entries = self.__entries(False)
        res = cur.execute(query)
        ret = []
        if not entries:
            return []
        for (round, table_idx, rank_swiss1, corp_score1, runner_score1, rank_swiss2, corp_score2, runner_score2, table_type) in res:
            if rank_swiss1 == None or rank_swiss2 == None:
                continue
            entry = Table(self)
            entry.player1 = entries[rank_swiss1-1]
            entry.player2 = entries[rank_swiss2-1]
            entry.corp_score1 = corp_score1
            entry.runner_score1 = runner_score1
            entry.corp_score2 = corp_score2
            entry.runner_score2 = runner_score2
            entry.table_type = table_type
            ret.append(entry)
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
        cur.execute("CREATE TABLE IF NOT EXISTS tournament_tables(tournament_id, round, table_idx, rank_swiss1, corp_score1, runner_score1, rank_swiss2, corp_score2, runner_score2, table_type)")

    def get_tournaments_api(self, cardpool):
        url = f'https://alwaysberunning.net/api/tournaments?cardpool={cardpool}&limit=100'
        response = cached_request(url)
        
        cur = self.con.cursor()

        insert = []
        for tournament in response:
            if not tournament['concluded']:
                continue
            tournament_id = int(tournament['id'])

            if cur.execute(f"SELECT id FROM tournaments WHERE id = {tournament_id}").fetchall():
                continue
            insert.append((tournament_id, tournament['title'], tournament['format'], tournament['cardpool'], tournament['mwl'], 0))

            if tournament['matchdata']:
                self.get_matchdata_api(tournament_id)

        cur.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?)", insert)

        self.con.commit()

    def __parse_cobra(id, data):
        player_data = data['players']
        def rank_swiss_player(id):
            for p in player_data:
                if p['id'] == id:
                    return p['rank']
            None

        insert = []
        for (round_idx,round_data) in enumerate(data['rounds']):
            for (table_idx, table_data) in enumerate(round_data): 
                if not 'player1' in table_data:
                    print(f"Wrong format for tourney {id}")
                    return
                
                r1 = rank_swiss_player(table_data['player1']['id'])
                r2 = rank_swiss_player(table_data['player2']['id'])
                if r2 is None or r1 is None:
                    continue # bye

                is_elim = 'eliminationGame' in table_data and table_data['eliminationGame']
                is_241 = 'twoForOne' in table_data and table_data['twoForOne']
                table_type = None
                if 'intentionalDraw' in table_data and table_data['intentionalDraw']:
                    table_type = 'intentionalDraw'
                if is_241:
                    table_type = 'twoForOne'
                elif is_elim:
                    table_type = 'eliminationGame'

                corp1_score = 0
                runner1_score = 0
                corp2_score = 0
                runner2_score = 0
                if is_elim:
                    win1 = table_data['player1']['winner']
                    is_corp1 = table_data['player1']['role'] == 'corp'
                    if win1:
                        corp1_score = 1 if is_corp1 else 0
                        runner1_score = 0 if is_corp1 else 1
                    else:
                        corp2_score = 0 if is_corp1 else 1
                        runner2_score = 1 if is_corp1 else 0
                else:
                    def get(player, score):
                        value = table_data[player][score]
                        return 1 if value and value > 0 else 0
                    runner1_score = get('player1','runnerScore') 
                    runner2_score = get('player2','runnerScore') 
                    corp1_score = get('player1','corpScore')
                    corp2_score = get('player2','corpScore')

                    if runner1_score + runner2_score + corp1_score + corp2_score == 0:
                        print(f"Weird score in table {round_idx}.{table_idx} for tourney {id}")
                        continue

                insert.append((id, round_idx, table_idx, r1, corp1_score, runner1_score, r2, corp2_score, runner2_score, table_type))
        return insert

    def __parse_aesops(id, data):
        player_data = data['players']
        def rank_swiss_player(id):
            for p in player_data:
                if p['id'] == id:
                    return p['rank']
            None

        insert = []
        for (round_idx,round_data) in enumerate(data['rounds']):
            for (table_idx, table_data) in enumerate(round_data): 
                corp = rank_swiss_player(table_data['corpPlayer'])
                runner = rank_swiss_player(table_data['runnerPlayer'])

                table_type = None
                if 'winner_id' in table_data:
                    # old Aesops tournaments have unparseable winner_id
                    continue 

                if table_type is None:
                    corp_score = 1 if int(table_data['corpScore']) > 0 else 0
                    runner_score = 1 if int(table_data['runnerScore']) > 0 else 0
                else:
                    continue

                insert.append((id, round_idx, table_idx, corp, corp_score, 0, runner, 0, runner_score, table_type))
        return insert
    
    def get_matchdata_api(self, id):
        data = cached_request(f'https://alwaysberunning.net/tjsons/{id}.json')
        if data == None:
            return
        
        insert = []
        uploadedFrom = data['uploadedFrom'] if 'uploadedFrom' in data else None
        if 'version' in data:
            uploadedFrom = 'NTRM'
        
        if uploadedFrom == 'Cobra' or uploadedFrom == 'NTRM':
            insert = ABR.__parse_cobra(id, data)
        elif uploadedFrom == 'AesopsTables':
            insert = ABR.__parse_aesops(id, data)
        else:
            print(f'Data from {uploadedFrom} for {id} not supported')

        cur = self.con.cursor()     
        cur.executemany("INSERT INTO tournament_tables VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", insert)
        self.con.commit()

    def get_tournaments(self, cardpool, format = None, banlist = None):
        cur = self.con.cursor()
        query = f"SELECT id, name, updated_at FROM tournaments card WHERE cardpool='{cardpool}'"
        if format:
            query += f" AND format = '{format}'"
        if banlist:
            query += f" AND banlist LIKE '%{banlist}'"

        res = cur.execute(query)
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
    abr = ABR()
    #abr.get_tournaments_api('tai')
    ts = abr.get_tournaments('tai')
    emea = Tournament(abr, 3779, '2023 EMEA Continentals')
    #emea.get_entries_api()
    print(emea.top_cut())