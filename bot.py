
import os
import asyncio
import requests
from telegram import Bot
from flask import Flask
from threading import Thread
import logging
import json
import time
import nest_asyncio
from deep_translator import GoogleTranslator

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

nest_asyncio.apply()  # permet asyncio dans Render

# ===================== CONFIG =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion"

bot = Bot(token=TOKEN)

# ===================== MÉTÉO =====================
LAST_WEATHER = None

def get_weather():
    global LAST_WEATHER
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url, timeout=10).json()
        desc = r['weather'][0]['description']
        temp = round(r['main']['temp'], 1)
        msg = f"Meteo a {CITY} : {desc}, {temp}°C"
        if msg == LAST_WEATHER:
            return None
        LAST_WEATHER = msg
        return msg
    except:
        return "Erreur recuperation meteo"

async def send_weather():
    try:
        msg = get_weather()
        if msg:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        logging.error(f"Erreur send_weather: {e}")

# ===================== NEWS =====================
SEEN_NEWS_FILE = "seen_news.json"
RESET_INTERVAL = 24 * 3600

def load_seen_news():
    if os.path.exists(SEEN_NEWS_FILE):
        with open(SEEN_NEWS_FILE, "r") as f:
            data = json.load(f)
            if time.time() - data.get("ts", 0) > RESET_INTERVAL:
                return set()
            return set(data.get("urls", []))
    return set()

def save_seen_news(seen):
    with open(SEEN_NEWS_FILE, "w") as f:
        json.dump({"ts": time.time(), "urls": list(seen)}, f)

async def send_news():
    try:
        seen = load_seen_news()
        new_articles = []

        # FR toutes categories
        url_fr = f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=15&apiKey={NEWS_API_KEY}"
        new_articles.extend(requests.get(url_fr, timeout=10).json().get("articles", []))

        # EN categories health, science, technology
        for cat in ["health", "science", "technology"]:
            url_en = f"https://newsapi.org/v2/top-headlines?language=en&category={cat}&pageSize=10&apiKey={NEWS_API_KEY}"
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
            msg = f"{title}\n{desc}\n{link}"

            try:
                if img:
                    await bot.send_photo(chat_id=CHAT_ID, photo=img, caption=msg[:1000])
                else:
                    await bot.send_message(chat_id=CHAT_ID, text=msg[:4000])
                sent_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Erreur envoi news: {e}")

        save_seen_news(seen)

        if sent_count == 0:
            await bot.send_message(chat_id=CHAT_ID, text="Pas de nouvelles inédites")
    except Exception as e:
        logging.error(f"Erreur recuperation news: {e}")
        await bot.send_message(chat_id=CHAT_ID, text="Erreur recuperation news")

# ===================== CITATIONS =====================
SEEN_QUOTE_FILE = "seen_quotes.json"

def load_seen_quotes():
    if os.path.exists(SEEN_QUOTE_FILE):
        with open(SEEN_QUOTE_FILE, "r") as f:
            data = json.load(f)
            if time.time() - data.get("ts", 0) > RESET_INTERVAL:
                return set()
            return set(data.get("quotes", []))
    return set()

def save_seen_quotes(seen):
    with open(SEEN_QUOTE_FILE, "w") as f:
        json.dump({"ts": time.time(), "quotes": list(seen)}, f)

async def send_quote():
    seen = load_seen_quotes()
    try:
        for _ in range(10):
            r = requests.get("https://api.quotable.io/random", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            content = data.get("content")
            author = data.get("author", "Inconnu")
            if not content or content in seen:
                continue

            seen.add(content)
            save_seen_quotes(seen)

            # Traduction FR
            try:
                translation = GoogleTranslator(source='auto', target='fr').translate(content)
            except:
                translation = "Erreur traduction"

            msg = f"Citation originale:\n{content}\nAuteur : {author}\nTraduction FR:\n{translation}"
            await bot.send_message(chat_id=CHAT_ID, text=msg[:4000])
            return

        await bot.send_message(chat_id=CHAT_ID, text="Pas de nouvelles citations inédites")
    except Exception as e:
        logging.error(f"Erreur send_quote: {e}")

# ===================== SCHEDULER =====================
async def scheduler_loop():
    while True:
        try:
            # Ordre : citation, meteo, news
            await asyncio.gather(send_quote(), send_weather(), send_news())
        except Exception as e:
            logging.error(f"Erreur scheduler_loop: {e}")
        await asyncio.sleep(5 * 60)  # toutes les 5 min pour test

# ===================== KEEP ALIVE =====================
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ===================== MAIN =====================
if __name__ == "__main__":
    Thread(target=run_flask).start()
    asyncio.run(scheduler_loop())
