import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_NAME = "proxy_server"

class Database:
    def __init__(self):
        try:
            self.db = psycopg2.connect(
                user="postgres",
                password="root",
                host="127.0.0.1",
                port="5432"
            )
            self.db.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        except psycopg2.Error as error:
            print("Ошибка подключении к базе дданных", error)

        try:
            self.cursor = self.db.cursor()
            self.cursor.execute("CREATE DATABASE " + DB_NAME)
            print("База данных создана")
        except psycopg2.Error as error:
            if error.pgcode == "42P04":
                print("База данных уже существует")
            else:
                print("Ошибка при создании базы данных", error)
        finally:
            self.cursor.close()

        try:
            self.cursor = self.db.cursor()
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS requests (
                    id      SERIAL PRIMARY KEY,
                    host    TEXT NOT NULL,
                    request TEXT NOT NULL
                );""")
            print("Таблица requests создана")
        except psycopg2.Error as error:
            print("Ошибка при создании таблицы", error)
        finally:
            self.cursor.close()

    def insert_request(self, req: str, host: str, tls: int):
        cur = self.db.cursor()
        cur.execute("INSERT INTO requests(host, request, tls) VALUES(%s, %s, %s)", [host, req, tls])
        cur.close()

    def select_all_requests(self):
        cur = self.db.cursor()
        cur.execute("SELECT * FROM requests")
        return cur.fetchall()

    def select_request_by_id(self, id):
        cur = self.db.cursor()
        cur.execute("SELECT * FROM requests WHERE id=%s", [id])
        return cur.fetchone()
