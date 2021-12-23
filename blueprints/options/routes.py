from flask import Blueprint, render_template
from database import Database

from utils import read_config

app = Blueprint('options', __name__, template_folder="templates")
_config = read_config("config.json")
_DB = Database(_config)


@app.route("/")
def options():
    return render_template("options.html")


@app.route("/clear_db")
def clear_db():
    _DB.execute(_DB.CLEAR)
    return render_template("notification.html", headers=["База данных успешно очищена"], response=["А вот так вот просто, да"])


@app.route("/reset_db")
def reset_db():
    _DB.execute(_DB.DROP)
    _DB.execute(_DB.INIT)
    return render_template("notification.html", headers=["База данных успешно пересоздана"], response=["А вот теперь индексы с 1 начнутся"])
