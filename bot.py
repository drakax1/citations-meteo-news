
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

# ===================== RESET FICHIERS =====================
for f in ["seen_urls.json", "seen_quotes.json"]:
    if os.path.exists(f):
        os.remove(f)
        logging.info(f"Fichier {f} supprimé pour reset complet")

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
        return f"{city['name']} : {desc}\nTempérature : {temp:.2f}°C (ressentie {feels_like:.2f}°C)\nHumidité : {humidity}% | Vent : {wind:.2f} m/s"
    except Exception as e:
        logging.error(f"Erreur récupération météo pour {city['name']}: {e}")
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

    try:
        resp = requests.get(f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=15&apiKey={NEWS_API_KEY}", timeout=10)
        data = resp.json()
        if data.get("status") != "ok":
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Erreur NewsAPI FR: {data}")
            logging.error(f"Erreur NewsAPI FR: {data}")
        else:
            new_articles.extend(data.get("articles", []))
    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Exception NewsAPI FR: {e}")
        logging.error(f"Exception NewsAPI FR: {e}")

    for cat in ["health", "science", "technology"]:
        try:
            resp = requests.get(f"https://newsapi.org/v2/top-headlines?language=en&category={cat}&pageSize=10&apiKey={NEWS_API_KEY}", timeout=10)
            data = resp.json()
            if data.get("status") != "ok":
                await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Erreur NewsAPI EN ({cat}): {data}")
                logging.error(f"Erreur NewsAPI EN ({cat}): {data}")
            else:
                new_articles.extend(data.get("articles", []))
        except Exception as e:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Exception NewsAPI EN ({cat}): {e}")
            logging.error(f"Exception NewsAPI EN ({cat}): {e}")

    if not new_articles:
        await bot.send_message(chat_id=CHAT_ID, text="⚠️ Pas d'articles récupérés cette fois.")
        logging.info("Pas d'articles récupérés cette fois.")
        return

    news_sent = False
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
            news_sent = True
            await asyncio.sleep(1)
        except Exception as e:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Erreur envoi article: {e}")
            logging.error(f"Erreur envoi article: {e}")
            continue

    if not news_sent:
        await bot.send_message(chat_id=CHAT_ID, text="Pas de nouvelles fraîches.")
        logging.info("Aucun article envoyé après filtrage des doublons.")

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
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Erreur récupération ou traduction citation: {e}")
            logging.error(f"Erreur citation: {e}")
            continue

# ===================== SCHEDULER =====================
async def scheduler_loop():
    while True:
        try:
            await send_quote()
            await send_weather()
            await send_news()
        except Exception as e:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Erreur scheduler: {e}")
            logging.error(f"Erreur scheduler: {e}")
        await asyncio.sleep(5*60)

# ===================== MAIN =====================
async def main():
    asyncio.create_task(scheduler_loop())
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
