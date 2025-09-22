
import os
import asyncio
import requests
from telegram import Bot
from flask import Flask
from threading import Thread
import logging
import json
import time

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
SEEN_FILE = "seen_urls.json"
RESET_INTERVAL = 24 * 3600  # reset toutes les 24h

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            data = json.load(f)
            if time.time() - data.get("ts", 0) > RESET_INTERVAL:
                return set()
            return set(data.get("urls", []))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump({"ts": time.time(), "urls": list(seen)}, f)

async def send_news():
    try:
        seen = load_seen()
        new_articles = []

        # FR toutes catégories
        url_fr = f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=5&apiKey={NEWS_API_KEY}"
        new_articles.extend(requests.get(url_fr, timeout=10).json().get("articles", []))

        # EN : health, science, technology
        for cat in ["health", "science", "technology"]:
            url_en = f"https://newsapi.org/v2/top-headlines?language=en&category={cat}&pageSize=3&apiKey={NEWS_API_KEY}"
            new_articles.extend(requests.get(url_en, timeout=10).json().get("articles", []))

        sent_count = 0
        for art in new_articles:
            url = art.get("url")
            if not url or url in seen:
                continue

            seen.add(url)

            title = art.get("title", "Sans titre")
            desc = art.get("description", "")
            link = url
            img = art.get("urlToImage")

            msg = f"📰 {title}\n{desc}\n{link}"

            try:
                if img:
                    await bot.send_photo(chat_id=CHAT_ID, photo=img, caption=msg[:1000])
                else:
                    await bot.send_message(chat_id=CHAT_ID, text=msg[:4000])
                sent_count += 1
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Erreur envoi news: {e}")

        save_seen(seen)

        if sent_count == 0:
            await bot.send_message(chat_id=CHAT_ID, text="📰 Pas de nouvelles inédites")

    except Exception as e:
        logging.error(f"Erreur récupération news: {e}")
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

# ===================== SCHEDULER =====================
async def scheduler_loop():
    last_weather_ts = 0
    last_news_ts = 0
    last_quote_ts = 0

    while True:
        now = time.time()

        # météo 30 min
        if now - last_weather_ts >= 30*60:
            await send_weather()
            last_weather_ts = now

        # news 10 min
        if now - last_news_ts >= 10*60:
            await send_news()
            last_news_ts = now

        # citation 20 min
        if now - last_quote_ts >= 20*60:
            await send_quote()
            last_quote_ts = now

        await asyncio.sleep(30)

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

# ===================== MAIN =====================
if __name__ == "__main__":
    keep_alive()
    asyncio.run(scheduler_loop())
