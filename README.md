# Proxy-server HTTP/HTTPS на Python

Перед запуском нужно настроить `config.json`, чтобы он мог залогиниться в БД.
> Если указанной `db_database` не существует, она будет создана
Прокси может работать и без подключения к БД, но для веб-интерфейса оно необходимо.

Работает с PostgreSQL

-----------------

Запуск прокси:
```
python3 main_proxy.py
```

Запуск веб-интерфейса:
```
python3 main_interface.py
```

Функционал:
```
/ – список запросов
/request - отправка кастомного запроса
/requests/id – вывод одного запроса
/repeat/id – повтор одного запроса
/param-check/id – проверка уязвимости значений определённого параметра
/param-miner/id - проверка на нахождение уязвимого параметра (Param-miner)
/clear_db - очистить таблицу базы данных (TRUNCATE)
/reset_db - удалить таблицу и создать заново
```

Есть встроенный декодер из `gzip` и `gzip + chunked` при просмотре ответов через веб-интерфейс.
