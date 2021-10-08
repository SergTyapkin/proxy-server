import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class Database:
    initialized = False

    def __init__(self, config):
        self.config = config
        try:
            self.db = psycopg2.connect(
                user=config["db_user"],
                password=config["db_password"],
                host=config["db_host"],
                port=config["db_port"]
            )
            self.db.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        except psycopg2.Error as error:
            print("Ошибка подключении к базе дданных", error)
            return

        try:
            self.cursor = self.db.cursor()
            self.cursor.execute("CREATE DATABASE " + config["db_database"])
            print("База данных создана")
        except psycopg2.Error as error:
            if error.pgcode == "42P04":
                print("База данных уже существует")
            else:
                print("Ошибка при создании базы данных", error)
                return
        finally:
            self.cursor.close()

        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS requests (
                    id      SERIAL PRIMARY KEY,
                    Host    TEXT NOT NULL,
                    Method  TEXT NOT NULL,
                    URL     TEXT NOT NULL,
                    Headers TEXT NOT NULL,
                    Cookie  TEXT NOT NULL,
                    Has_TLS BOOLEAN DEFAULT FALSE
                );""")
            print("Таблица requests создана")
        except psycopg2.Error as error:
            print("Ошибка при создании таблицы", error)
            return
        finally:
            self.cursor.close()

        self.initialized = True

    def insert_request(self, host: str, method: str, url: str, headers: str, cookie: str, tls: bool = False):
        if not self.initialized:
            print("База данных не была инициализирована. Операция отменена")
            return
        cur = self.db.cursor()
        cur.execute("INSERT INTO requests(host, Method, URL, Headers, Cookie, Has_TLS) VALUES(%s, %s, %s, %s, %s, %s)",
                    [host, method, url, headers, cookie, tls])
        cur.close()

    def select_all_requests(self):
        cur = self.db.cursor()
        cur.execute("SELECT * FROM requests ORDER BY id DESC LIMIT 500")
        return cur.fetchall(), [desc[0] for desc in cur.description]

    def select_request_by_id(self, id):
        cur = self.db.cursor()
        cur.execute("SELECT * FROM requests WHERE id=%s", [id])
        return cur.fetchone(), [desc[0] for desc in cur.description]

    def clear(self):
        cur = self.db.cursor()
        cur.execute("TRUNCATE TABLE requests")
        cur.close()

    def reset(self):
        cur = self.db.cursor()
        cur.execute("DROP TABLE requests")
        cur.close()
        cur = self.db.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS requests (
                id      SERIAL PRIMARY KEY,
                Host    TEXT NOT NULL,
                Method  TEXT NOT NULL,
                URL     TEXT NOT NULL,
                Headers TEXT NOT NULL,
                Cookie  TEXT NOT NULL,
                Has_TLS BOOLEAN DEFAULT FALSE
            );""")
        cur.close()
