
import requests
import schedule
import time
import json
import logging
from datetime import datetime, timedelta
from telegram import Bot
from flask import Flask
from threading import Thread
import os

# ===================== CONFIGURATION EN DUR =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion"

bot = Bot(token=TOKEN)

# ===================== LOGGING =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ===================== MÉTÉO =====================
def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        logging.info(f"Météo récupérée : {desc}, {temp}°C")
        return f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
    except Exception as e:
        logging.error(f"Erreur météo : {e}")
        return None

def get_alerts():
    try:
        url = f"https://api.openweathermap.org/data/2.5/onecall?lat=46.233&lon=7.366&appid={OWM_API_KEY}&lang=fr"
        r = requests.get(url).json()
        if "alerts" in r:
            alerts = [a['description'] for a in r['alerts']]
            return "\n⚠️ ALERTE MÉTÉO :\n" + "\n".join(alerts)
    except Exception as e:
        logging.error(f"Erreur alertes météo : {e}")
    return None

def send_weather():
    msg = get_weather()
    if msg:
        bot.send_message(chat_id=CHAT_ID, text=msg)
    alert = get_alerts()
    if alert:
        bot.send_message(chat_id=CHAT_ID, text=alert)

# ===================== NEWS =====================
LAST_NEWS_FILE = "last_news.json"
MAX_LAST_NEWS = 1000

# Charger news déjà envoyées
if os.path.exists(LAST_NEWS_FILE):
    with open(LAST_NEWS_FILE, "r") as f:
        last_news_ids = json.load(f)
else:
    last_news_ids = []

COUNTRIES_PRIORITY = ["ch", "fr", "be", "ca"]

def save_last_news():
    if len(last_news_ids) > MAX_LAST_NEWS:
        del last_news_ids[:-MAX_LAST_NEWS]
    with open(LAST_NEWS_FILE, "w") as f:
        json.dump(last_news_ids, f)

def get_news():
    try:
        all_articles = []
        for country in COUNTRIES_PRIORITY:
            url = (
                f"https://newsapi.org/v2/top-headlines?"
                f"country={country}&"
                f"language=fr&"
                f"pageSize=10&"
                f"apiKey={NEWS_API_KEY}"
            )
            r = requests.get(url).json()
            articles = r.get("articles", [])
            for a in articles:
                if a['url'] not in last_news_ids:
                    all_articles.append(a)
        if not all_articles:
            logging.info("Pas de nouvelles fraîches")
            return None
        # Trier par date et ne prendre que 5 max
        all_articles = sorted(all_articles, key=lambda x: x['publishedAt'], reverse=True)[:5]
        msg = "📰 Dernières actus :\n" + "\n".join([a['title'] for a in all_articles])
        # Ajouter aux news déjà envoyées
        for a in all_articles:
            last_news_ids.append(a['url'])
        save_last_news()
        logging.info(f"{len(all_articles)} news envoyées")
        return msg
    except Exception as e:
        logging.error(f"Erreur news : {e}")
        return None

def send_news():
    msg = get_news()
    if msg:
        bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== CITATIONS =====================
def get_quote():
    try:
        r = requests.get("https://api.quotable.io/random", timeout=10)
        r.raise_for_status()
        data = r.json()
        logging.info(f"Citation récupérée : {data['content']} — {data['author']}")
        return f"💡 Citation : {data['content']} — {data['author']}"
    except Exception as e:
        logging.error(f"Erreur citation : {e}")
        return None

def send_quote():
    msg = get_quote()
    if msg:
        bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== PLANIFICATION =====================
schedule.every(30).minutes.do(send_weather)
schedule.every(30).minutes.do(send_news)
schedule.every(30).minutes.do(send_quote)

# ===================== KEEP ALIVE POUR RENDER =====================
app = Flask('bot')

@app.route('/')
def home():
    logging.info("Ping reçu sur /")
    return "Bot is alive"

def run():
    logging.info("Flask server started")
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===================== BOUCLE PRINCIPALE =====================
if __name__ == "__main__":
    keep_alive()
    logging.info("Bot démarré et prêt")
    while True:
        schedule.run_pending()
        time.sleep(30)
