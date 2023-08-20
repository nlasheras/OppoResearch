from requests import cached_request
import sqlite3
import time

class Tournament:
    def __init__(self, parent, id, name):
        self.__abr = parent
        self.id = id
        self.name = name

    def __repr__(self):
        return f"ABR.Tournament({self.name},{self.id})"
    
class ABR:
    def __init__(self):
        self.con = sqlite3.connect("abr.db")
        self.__create_db()
        pass

    def __create_db(self):
        cur = self.con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS tournaments(id, name, format, cardpool, banlist, updated_at)")

    def get_tournaments_api(self, cardpool):
        url = f'https://alwaysberunning.net/api/tournaments?cardpool={cardpool}&type=4'
        response = cached_request(url)

        ret = []
        data = []
        now = int(time.time())
        for tournament in response:
            entry = {} 
            entry['id'] = tournament['id']
            entry['name'] = tournament['title']
            entry['format'] = tournament['format']
            entry['cardpool'] = tournament['cardpool']
            entry['banlist'] = tournament['mwl']
            ret.append(entry)
            data.append((int(entry['id']), entry['name'], entry['format'], entry['cardpool'], entry['banlist'], now))

        cur = self.con.cursor()
        cur.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?)", data)
        self.con.commit()
        return ret

    def get_tournaments(self, cardpool):
        cur = self.con.cursor()
        res = cur.execute("SELECT id, name, updated_at FROM tournaments WHERE format = 'standard'")
        ret = []
        for (id, name, updated_at) in res:
            ret.append(Tournament(self, id, name))
        return ret


if __name__ == "__main__":
    test = ABR()
    #test.get_tournaments_api('ph')
    print(test.get_tournaments('ph'))