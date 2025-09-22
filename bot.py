
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
def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        logging.info("Météo récupérée")
        return f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
    except Exception as e:
        logging.error(f"Erreur météo: {e}")
        return "Erreur récupération météo"

def get_alerts():
    try:
        url = f"https://api.openweathermap.org/data/2.5/onecall?lat=46.233&lon=7.366&appid={OWM_API_KEY}&lang=fr"
        r = requests.get(url).json()
        if "alerts" in r:
            alerts = [a['description'] for a in r['alerts']]
            logging.info("Alertes météo récupérées")
            return "\n⚠️ ALERTE MÉTÉO :\n" + "\n".join(alerts)
        return None
    except Exception as e:
        logging.error(f"Erreur alertes météo: {e}")
        return None

async def send_weather():
    msg = get_weather()
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        logging.info("Météo envoyée")
        alert = get_alerts()
        if alert:
            await bot.send_message(chat_id=CHAT_ID, text=alert)
            logging.info("Alertes envoyées")
    except Exception as e:
        logging.error(f"Erreur envoi météo: {e}")

# ===================== NEWS =====================
def get_news():
    try:
        now = datetime.now(timezone.utc)
        last_hour = now - timedelta(hours=1)
        url = (
            f"https://newsapi.org/v2/everything?"
            f"language=fr&"
            f"from={last_hour.isoformat()}&"
            f"to={now.isoformat()}&"
            f"sortBy=publishedAt&"
            f"pageSize=10&"
            f"apiKey={NEWS_API_KEY}"
        )
        r = requests.get(url).json()
        articles = r.get("articles", [])[:10]
        if not articles:
            return "📰 Pas de nouvelles fraîches cette heure-ci."
        logging.info("News récupérées")
        return "📰 Dernières actus :\n" + "\n".join([a['title'] for a in articles])
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
def get_quote():
    try:
        r = requests.get("https://api.quotable.io/random")
        data = r.json()
        logging.info("Citation récupérée")
        return f"💡 Citation : {data['content']} — {data['author']}"
    except Exception as e:
        logging.error(f"Erreur citation: {e}")
        return "Erreur récupération citation"

async def send_quote():
    msg = get_quote()
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        logging.info("Citation envoyée")
    except Exception as e:
        logging.error(f"Erreur envoi citation: {e}")

# ===================== PLANIFICATION =====================
async def scheduler_loop():
    while True:
        now = datetime.now()
        if now.minute == 0:
            await send_weather()
        elif now.minute == 5:
            await send_news()
        elif now.minute == 10:
            await send_quote()
        await asyncio.sleep(60)

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
