
import os
import asyncio
import requests
from datetime import datetime, timedelta
from telegram import Bot
from flask import Flask
from threading import Thread
import logging
import json

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# ===================== CONFIG =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion"
NEWS_FILE = "last_news.json"

bot = Bot(token=TOKEN)

# ===================== MÉTÉO =====================
last_weather = None

def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url, timeout=10).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        msg = f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
        logging.info(f"[DEBUG] Météo récupérée: {msg}")
        return msg
    except Exception as e:
        logging.error(f"[ERROR] Erreur météo: {e}")
        return "Erreur récupération météo"

async def send_weather():
    global last_weather
    msg = get_weather()
    if msg != last_weather:
        try:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            logging.info("[DEBUG] Météo envoyée")
            last_weather = msg
        except Exception as e:
            logging.error(f"[ERROR] Envoi météo: {e}")
    else:
        logging.info("[DEBUG] Météo identique, pas de doublon envoyé")

# ===================== NEWS =====================
def load_last_news():
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r") as f:
            data = json.load(f)
            ts = datetime.fromisoformat(data.get("timestamp"))
            # reset si >24h
            if datetime.utcnow() - ts > timedelta(hours=24):
                return set()
            return set(data.get("titles", []))
    return set()

def save_last_news(titles):
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "titles": list(titles)
    }
    with open(NEWS_FILE, "w") as f:
        json.dump(data, f)

async def send_news():
    last_news_ids = load_last_news()
    try:
        countries = ["ch","fr","be","ca"]
        all_new_articles = []
        for country in countries:
            url = f"https://newsapi.org/v2/top-headlines?language=fr&country={country}&pageSize=10&apiKey={NEWS_API_KEY}"
            r = requests.get(url, timeout=10).json()
            articles = r.get("articles", [])
            new_articles = [a for a in articles if a['title'] not in last_news_ids]
            if new_articles:
                all_new_articles.extend(new_articles)
                break  # Priorité pays, on prend le premier qui a du contenu
        if not all_new_articles:
            msg = "📰 Pas de nouvelles fraîches..."
            logging.info("[DEBUG] News: aucune nouvelle unique")
        else:
            titles = [a['title'] for a in all_new_articles]
            msg = "📰 Dernières actus :\n" + "\n".join(titles)
            last_news_ids.update(titles)
            save_last_news(last_news_ids)
            logging.info(f"[DEBUG] {len(titles)} nouvelles envoyées")
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        logging.error(f"[ERROR] Envoi news: {e}")
        await bot.send_message(chat_id=CHAT_ID, text="Erreur récupération news")

# ===================== CITATIONS =====================
async def send_quote():
    try:
        r = requests.get("https://api.quotable.io/random", timeout=10)
        if r.status_code == 200:
            data = r.json()
            msg = f"💡 Citation : {data.get('content','')} — {data.get('author','')}"
            logging.info("[DEBUG] Citation récupérée")
        else:
            msg = "💡 Pas de citation disponible"
            logging.error(f"[ERROR] Citation API status: {r.status_code}")
    except Exception as e:
        msg = "💡 Pas de citation disponible"
        logging.error(f"[ERROR] Erreur récupération citation: {e}")
    finally:
        try:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            logging.info("[DEBUG] Citation envoyée")
        except Exception as e:
            logging.error(f"[ERROR] Envoi citation: {e}")

# ===================== SCHEDULER 30MIN =====================
async def scheduler_loop():
    logging.info("[DEBUG] Scheduler démarré")
    while True:
        await asyncio.gather(
            send_weather(),
            send_news(),
            send_quote()
        )
        logging.info("[DEBUG] Attente 30 minutes avant le prochain envoi")
        await asyncio.sleep(30*60)  # 30 minutes

# ===================== KEEP ALIVE =====================
app = Flask('')
@app.route('/')
def home():
    logging.info("[DEBUG] Ping reçu sur /")
    return "Bot is alive"

def run():
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"[DEBUG] Flask server started on port {port}")
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===================== BOUCLE PRINCIPALE =====================
if __name__ == "__main__":
    keep_alive()
    asyncio.run(scheduler_loop())
