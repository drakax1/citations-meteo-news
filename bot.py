
import os
import asyncio
import requests
from telegram import Bot
import logging
import json
import time
import urllib3
import nest_asyncio
from deep_translator import GoogleTranslator
from fastapi import FastAPI
import uvicorn

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
nest_asyncio.apply()

# ===================== CONFIG =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITIES = [
    {"name": "Sierre"},
    {"name": "Sion"},
    {"name": "Martigny"},
    {"name": "Monthey"},
]

bot = Bot(token=TOKEN)
app = FastAPI()

# ===================== ENDPOINT PING =====================
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "pong"}

# ===================== MÉTÉO =====================
def get_weather_for_city(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city['name']}&appid={OWM_API_KEY}&units=metric&lang=fr"
        r = requests.get(url, timeout=10).json()
        desc = r['weather'][0]['description']
        temp = r['main']['temp']
        feels_like = r['main']['feels_like']
        humidity = r['main']['humidity']
        wind = r['wind']['speed']
        return f"{city['name']} : {desc}\nTempérature : {temp:.1f}°C (ressentie {feels_like:.1f}°C)\nHumidité : {humidity}% | Vent : {wind:.1f} m/s"
    except Exception as e:
        logging.error(f"Erreur météo pour {city['name']}: {e}")
        return f"{city['name']} : Erreur récupération météo"

async def send_weather():
    msg = "\n\n".join(get_weather_for_city(c) for c in CITIES)
    await bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== NEWS =====================
SEEN_NEWS_FILE = "seen_urls.json"
RESET_INTERVAL = 24 * 3600

def load_seen_news():
    if os.path.exists(SEEN_NEWS_FILE):
        with open(SEEN_NEWS_FILE) as f:
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

    # Récupération des articles français
    try:
        resp_fr = requests.get(f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=15&apiKey={NEWS_API_KEY}", timeout=10).json()
        if resp_fr.get("status") == "ok":
            new_articles.extend(resp_fr.get("articles", []))
        else:
            logging.error(f"Erreur NewsAPI FR: {resp_fr}")
            await bot.send_message(chat_id=CHAT_ID, text=f"Erreur NewsAPI FR: {resp_fr.get('message','?')}")
    except Exception as e:
        logging.error(f"Exception NewsAPI FR: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=f"Exception NewsAPI FR: {e}")

    # Récupération des articles EN
    for cat in ["health", "science", "technology"]:
        try:
            resp_en = requests.get(f"https://newsapi.org/v2/top-headlines?language=en&category={cat}&pageSize=10&apiKey={NEWS_API_KEY}", timeout=10).json()
            if resp_en.get("status") == "ok":
                new_articles.extend(resp_en.get("articles", []))
            else:
                logging.error(f"Erreur NewsAPI EN ({cat}): {resp_en}")
                await bot.send_message(chat_id=CHAT_ID, text=f"Erreur NewsAPI EN ({cat}): {resp_en.get('message','?')}")
        except Exception as e:
            logging.error(f"Exception NewsAPI EN ({cat}): {e}")
            await bot.send_message(chat_id=CHAT_ID, text=f"Exception NewsAPI EN ({cat}): {e}")

    # Envoi des articles
    news_sent = False
    for art in new_articles:
        url = art.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        title = art.get("title", "Sans titre")
        desc = art.get("description", "")
        img = art.get("urlToImage")
        msg = f"{title}\n{desc}\n{url}"
        try:
            if img:
                await bot.send_photo(chat_id=CHAT_ID, photo=img, caption=msg[:1000])
            else:
                await bot.send_message(chat_id=CHAT_ID, text=msg[:4000])
            news_sent = True
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Erreur envoi article: {e}")

    if not news_sent:
        await bot.send_message(chat_id=CHAT_ID, text="Pas de nouvelles fraîches.")

    save_seen_news(seen)

# ===================== CITATIONS =====================
SEEN_QUOTES_FILE = "seen_quotes.json"

def load_seen_quotes():
    if os.path.exists(SEEN_QUOTES_FILE):
        with open(SEEN_QUOTES_FILE) as f:
            data = json.load(f)
            return set(data.get("ids", []))
    return set()

def save_seen_quotes(seen):
    with open(SEEN_QUOTES_FILE, "w") as f:
        json.dump({"ids": list(seen)}, f)

async def send_quote():
    seen = load_seen_quotes()
    for _ in range(5):
        try:
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
        except Exception as e:
            logging.error(f"Erreur récupération citation: {e}")

# ===================== SCHEDULER =====================
async def scheduler_loop():
    # 1x au déploiement
    await send_quote()
    await send_weather()
    await send_news()

    while True:
        try:
            await send_quote()
            await send_weather()
            await send_news()
        except Exception as e:
            logging.error(f"Erreur scheduler: {e}")
        await asyncio.sleep(30*60)  # 30 minutes

# ===================== MAIN =====================
async def main():
    asyncio.create_task(scheduler_loop())
    # FastAPI en parallèle
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
