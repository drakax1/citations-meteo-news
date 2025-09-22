
import os
import asyncio
import requests
from telegram import Bot
from flask import Flask
from threading import Thread
import logging
import json
import time
import urllib3
import nest_asyncio
from deep_translator import GoogleTranslator

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===================== CONFIG =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion"

bot = Bot(token=TOKEN)
nest_asyncio.apply()  # permet asyncio dans Render

# ===================== MÉTÉO =====================
def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url, timeout=10).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        return f"Météo à {CITY} : {desc}, {temp}°C"
    except:
        return "Erreur récupération météo"

async def send_weather():
    msg = get_weather()
    await bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== NEWS =====================
SEEN_NEWS_FILE = "seen_urls.json"
RESET_INTERVAL = 24 * 3600  # reset toutes les 24h

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
    seen = load_seen_news()
    new_articles = []

    # FR toutes catégories
    url_fr = f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=15&apiKey={NEWS_API_KEY}"
    new_articles.extend(requests.get(url_fr, timeout=10).json().get("articles", []))

    # EN catégories health, science, technology
    for cat in ["health", "science", "technology"]:
        url_en = f"https://newsapi.org/v2/top-headlines?language=en&category={cat}&pageSize=10&apiKey={NEWS_API_KEY}"
        new_articles.extend(requests.get(url_en, timeout=10).json().get("articles", []))

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
            await asyncio.sleep(1)
        except:
            continue

    save_seen_news(seen)

# ===================== CITATIONS =====================
SEEN_QUOTES_FILE = "seen_quotes.json"

def load_seen_quotes():
    if os.path.exists(SEEN_QUOTES_FILE):
        with open(SEEN_QUOTES_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("ids", []))
    return set()

def save_seen_quotes(seen):
    with open(SEEN_QUOTES_FILE, "w") as f:
        json.dump({"ids": list(seen)}, f)

async def send_quote():
    seen = load_seen_quotes()
    for _ in range(5):  # max 5 essais pour trouver une citation non vue
        r = requests.get("https://api.quotable.io/random", timeout=15, verify=False)
        data = r.json()
        cid = data.get("_id")
        if cid in seen:
            continue

        original = data.get("content")
        author = data.get("author", "Inconnu")
        traduction = GoogleTranslator(source='en', target='fr').translate(original)

        msg = f"Citation originale :\n{original}\n\nTraduction française :\n{traduction} — {author}"

        await bot.send_message(chat_id=CHAT_ID, text=msg)
        seen.add(cid)
        save_seen_quotes(seen)
        return

# ===================== SCHEDULER =====================
async def scheduler_loop():
    while True:
        try:
            await asyncio.gather(send_quote(), send_weather(), send_news())
        except Exception as e:
            logging.error(f"Erreur dans scheduler_loop: {e}")
        await asyncio.sleep(15*60)  # toutes les 15 min

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
    asyncio.get_event_loop().create_task(scheduler_loop())
    asyncio.get_event_loop().run_forever()
