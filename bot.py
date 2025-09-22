
import requests
import schedule
import asyncio
import time
from datetime import datetime, timedelta, timezone
from telegram import Bot
from telegram.ext import ApplicationBuilder
from flask import Flask
from threading import Thread
import logging
import nest_asyncio

# Permet d'exécuter asyncio sur Colab / Jupyter
nest_asyncio.apply()

# ===================== LOGGING =====================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== CONFIGURATION EN DUR =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion,CH"

bot = Bot(token=TOKEN)
app = Flask(__name__)

# ===================== MÉTÉO =====================
async def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        msg = f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
        logger.info(f"Météo récupérée : {msg}")
        return msg
    except Exception as e:
        logger.error(f"Erreur météo: {e}")
        return "Erreur lors de la récupération de la météo."

async def get_alerts():
    try:
        url = f"https://api.openweathermap.org/data/2.5/onecall?lat=46.233&lon=7.366&appid={OWM_API_KEY}&lang=fr"
        r = requests.get(url).json()
        if "alerts" in r:
            alerts = [a['description'] for a in r['alerts']]
            msg = "\n⚠️ ALERTE MÉTÉO :\n" + "\n".join(alerts)
            logger.info(f"Alerte météo : {msg}")
            return msg
        return None
    except Exception as e:
        logger.error(f"Erreur alertes météo: {e}")
        return None

async def send_weather():
    msg = await get_weather()
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    alert = await get_alerts()
    if alert:
        await bot.send_message(chat_id=CHAT_ID, text=alert)
    logger.info("Météo envoyée")

# ===================== NEWS =====================
async def get_news():
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
        msg = "📰 Dernières actus :\n" + "\n".join([a['title'] for a in articles])
        logger.info(f"News récupérées : {msg}")
        return msg
    except Exception as e:
        logger.error(f"Erreur news: {e}")
        return "Erreur lors de la récupération des news."

async def send_news():
    msg = await get_news()
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    logger.info("News envoyées")

# ===================== CITATIONS =====================
async def get_quote():
    try:
        r = requests.get("https://api.quotable.io/random")
        data = r.json()
        msg = f"💡 Citation : {data['content']} — {data['author']}"
        logger.info(f"Citation récupérée : {msg}")
        return msg
    except Exception as e:
        logger.error(f"Erreur citation: {e}")
        return "Erreur lors de la récupération de la citation."

async def send_quote():
    msg = await get_quote()
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    logger.info("Citation envoyée")

# ===================== PLANIFICATION =====================
async def job_loop():
    while True:
        now = datetime.now()
        h, m = now.hour, now.minute
        # Citations : minute 0
        if m == 0:
            await send_quote()
        # Météo : minute 5
        if m == 5:
            await send_weather()
        # News : minute 10
        if m == 10:
            await send_news()
        await asyncio.sleep(60)  # vérifie chaque minute

# ===================== KEEP ALIVE POUR RENDER =====================
@app.route('/')
def home():
    return "Bot is alive"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ===================== MAIN =====================
async def main():
    # Démarrer Flask en thread séparé
    t = Thread(target=run_flask)
    t.start()
    logger.info("Flask server started")
    # Lancer la boucle des jobs
    await job_loop()

if __name__ == "__main__":
    asyncio.run(main())
