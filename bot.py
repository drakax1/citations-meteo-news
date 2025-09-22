
import requests
import schedule
import time
from datetime import datetime, timedelta
from telegram import Bot
from flask import Flask
from threading import Thread
import logging
import json
import os

# ===================== LOGS =====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === CONFIGURATION EN DUR ===
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion"
bot = Bot(token=TOKEN)

# ===================== HISTOIRE NEWS =====================
LAST_NEWS_FILE = "last_news.json"
if os.path.exists(LAST_NEWS_FILE):
    with open(LAST_NEWS_FILE, "r") as f:
        last_news_ids = set(json.load(f))
else:
    last_news_ids = set()

def save_last_news():
    with open(LAST_NEWS_FILE, "w") as f:
        json.dump(list(last_news_ids), f)

# ===================== MÉTÉO =====================
def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url).json()
        logging.info(f"Météo API response: {r}")
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        return f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
    except Exception as e:
        logging.error(f"Erreur récupération météo: {e}")
        return "🌤️ Impossible de récupérer la météo."

def get_alerts():
    try:
        url = f"https://api.openweathermap.org/data/2.5/onecall?lat=46.233&lon=7.366&appid={OWM_API_KEY}&lang=fr"
        r = requests.get(url).json()
        logging.info(f"Alert API response: {r}")
        if "alerts" in r:
            alerts = [a['description'] for a in r['alerts']]
            return "\n⚠️ ALERTE MÉTÉO :\n" + "\n".join(alerts)
    except Exception as e:
        logging.error(f"Erreur récupération alertes: {e}")
    return None

def send_weather():
    msg = get_weather()
    logging.info(f"Envoi météo: {msg}")
    bot.send_message(chat_id=CHAT_ID, text=msg)
    alert = get_alerts()
    if alert:
        logging.info(f"Envoi alertes: {alert}")
        bot.send_message(chat_id=CHAT_ID, text=alert)

# ===================== NEWS =====================
COUNTRIES = ["ch", "fr", "be", "ca"]
def get_news():
    try:
        now = datetime.utcnow()
        from_time = now - timedelta(minutes=60)  # dernière heure
        all_articles = []
        for country in COUNTRIES:
            url = (
                f"https://newsapi.org/v2/top-headlines?"
                f"country={country}&"
                f"language=fr&"
                f"from={from_time.isoformat()}&"
                f"to={now.isoformat()}&"
                f"pageSize=10&"
                f"apiKey={NEWS_API_KEY}"
            )
            r = requests.get(url).json()
            logging.info(f"News API response ({country}): {r}")
            articles = r.get("articles", [])
            for a in articles:
                if a['title'] not in last_news_ids:
                    all_articles.append(a)
        if not all_articles:
            return "📰 Pas de nouvelles fraîches cette période."
        messages = []
        for a in all_articles[:5]:
            messages.append(a['title'])
            last_news_ids.add(a['title'])
        save_last_news()
        return "📰 Dernières actus :\n" + "\n".join(messages)
    except Exception as e:
        logging.error(f"Erreur récupération news: {e}")
        return "📰 Impossible de récupérer les news."

def send_news():
    msg = get_news()
    logging.info(f"Envoi news: {msg}")
    bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== CITATIONS =====================
def get_quote():
    try:
        r = requests.get("https://api.quotable.io/random")
        logging.info(f"Citation API response: {r.text}")
        data = r.json()
        return f"💡 Citation : {data['content']} — {data['author']}"
    except Exception as e:
        logging.error(f"Erreur récupération citation: {e}")
        return "💡 Impossible de récupérer une citation."

def send_quote():
    msg = get_quote()
    logging.info(f"Envoi citation: {msg}")
    bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== PLANIFICATION =====================
schedule.every(30).minutes.do(send_weather)
schedule.every(30).minutes.do(send_news)
schedule.every(30).minutes.do(send_quote)

# ===================== KEEP ALIVE =====================
app = Flask('bot')
@app.route('/')
def home():
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
    logging.info("Bot started, running scheduled jobs every 30 minutes.")
    while True:
        schedule.run_pending()
        time.sleep(10)
