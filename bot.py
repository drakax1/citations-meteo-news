
import os
import asyncio
import requests
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
CITY = "Sion"

bot = Bot(token=TOKEN)

# ===================== MÉTÉO =====================
last_weather = None

def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url, timeout=10).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        return f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
    except:
        return "Erreur récupération météo"

async def send_weather():
    global last_weather
    msg = get_weather()
    if msg != last_weather:
        try:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            last_weather = msg
        except:
            pass

# ===================== NEWS =====================
async def send_news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=10&apiKey={NEWS_API_KEY}"
        r = requests.get(url, timeout=10).json()
        articles = r.get("articles", [])
        if not articles:
            msg = "📰 Pas de nouvelles disponibles"
        else:
            titles = [a['title'] for a in articles]
            msg = "📰 Dernières actus :\n" + "\n".join(titles)
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except:
        await bot.send_message(chat_id=CHAT_ID, text="Erreur récupération news")

# ===================== CITATIONS =====================
async def send_quote():
    try:
        r = requests.get("https://api.quotable.io/random", timeout=5)
        data = r.json()
        msg = f"💡 Citation : {data.get('content','')} — {data.get('author','')}"
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except:
        await bot.send_message(chat_id=CHAT_ID, text="💡 Pas de citation disponible")

# ===================== SCHEDULER 30MIN =====================
async def scheduler_loop():
    while True:
        await asyncio.gather(
            send_weather(),
            send_news(),
            send_quote()
        )
        await asyncio.sleep(30*60)  # 30 minutes

# ===================== KEEP ALIVE =====================
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===================== BOUCLE PRINCIPALE =====================
if __name__ == "__main__":
    keep_alive()
    asyncio.run(scheduler_loop())
