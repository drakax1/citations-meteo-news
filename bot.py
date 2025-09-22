
import os
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from telegram import Bot
from flask import Flask
from threading import Thread
import logging

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# ===================== CONFIG =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion,CH"

bot = Bot(token=TOKEN)

# ===================== MÉTÉO =====================
last_weather = None

def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        msg = f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
        logging.info(f"Météo récupérée: {msg}")
        return msg
    except Exception as e:
        logging.error(f"Erreur météo: {e}")
        return "Erreur récupération météo"

async def send_weather():
    global last_weather
    msg = get_weather()
    if msg != last_weather:
        try:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            logging.info("Météo envoyée")
            last_weather = msg
        except Exception as e:
            logging.error(f"Erreur envoi météo: {e}")
    else:
        logging.info("Météo identique, pas de doublon envoyé")

# ===================== NEWS =====================
last_news_ids = set()

def get_news():
    global last_news_ids
    try:
        url = f"https://newsapi.org/v2/top-headlines?language=fr&country=ch&pageSize=10&apiKey={NEWS_API_KEY}"
        r = requests.get(url).json()
        articles = r.get("articles", [])
        new_articles = [a for a in articles if a['title'] not in last_news_ids]
        if not new_articles:
            logging.info("Aucune nouvelle unique à envoyer")
            return "📰 Pas de nouvelles fraîches..."
        last_news_ids.update([a['title'] for a in new_articles])
        logging.info(f"{len(new_articles)} nouvelles récupérées")
        return "📰 Dernières actus :\n" + "\n".join([a['title'] for a in new_articles])
    except Exception as e:
        logging.error(f"Erreur news: {e}")
        return "Erreur récupération news"

async def send_news():
    msg = get_news()
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        logging.info("News envoyées")
    except Exception as e:
        logging.error(f"Erreur envoi news: {e}")

# ===================== CITATIONS =====================
async def send_quote():
    try:
        r = requests.get("https://api.quotable.io/random", timeout=10)
        if r.status_code == 200:
            data = r.json()
            msg = f"💡 Citation : {data.get('content','')} — {data.get('author','')}"
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            logging.info("Citation envoyée")
        else:
            logging.error(f"Erreur API citation status code: {r.status_code}")
    except Exception as e:
        logging.error(f"Erreur récupération citation: {e}")

# ===================== SCHEDULER 30MIN =====================
async def scheduler_loop():
    while True:
        logging.info("Scheduler tick")
        await asyncio.gather(
            send_weather(),
            send_news(),
            send_quote()
        )
        logging.info("Attente 30 minutes")
        await asyncio.sleep(30*60)  # 30 minutes

# ===================== KEEP ALIVE =====================
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive"

def run():
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Flask server started on port {port}")
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===================== BOUCLE PRINCIPALE =====================
if __name__ == "__main__":
    keep_alive()
    asyncio.run(scheduler_loop())
