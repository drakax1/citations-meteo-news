
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
from aiohttp import web

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
nest_asyncio.apply()  # permet asyncio partout

# ===================== CONFIG =====================
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITIES = [
    {"name": "Sierre", "code": "3960"},
    {"name": "Sion", "code": "1950"},
    {"name": "Martigny", "code": "1920"},
    {"name": "Monthey", "code": "1870"},
]

bot = Bot(token=TOKEN)

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
    except:
        return f"{city['name']} : Erreur récupération météo"

async def send_weather():
    messages = []
    for city in CITIES:
        weather = await asyncio.to_thread(get_weather_for_city, city)
        messages.append(weather)
    msg = "\n\n".join(messages)
    await bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== NEWS =====================
SEEN_NEWS_FILE = "seen_urls.json"
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
    seen = load_seen_news()
    new_articles = []

    # FR toutes catégories
    fr_data = await asyncio.to_thread(requests.get, f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=15&apiKey={NEWS_API_KEY}", timeout=10)
    new_articles.extend(fr_data.json().get("articles", []))

    # EN catégories health, science, technology
    for cat in ["health", "science", "technology"]:
        en_data = await asyncio.to_thread(requests.get, f"https://newsapi.org/v2/top-headlines?language=en&category={cat}&pageSize=10&apiKey={NEWS_API_KEY}", timeout=10)
        new_articles.extend(en_data.json().get("articles", []))

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
    for _ in range(5):
        r = await asyncio.to_thread(requests.get, "https://api.quotable.io/random", timeout=15, verify=False)
        data = r.json()
        cid = data.get("_id")
        if cid in seen:
            continue

        original = data.get("content")
        author = data.get("author", "Inconnu")
        traduction = await asyncio.to_thread(GoogleTranslator(source='en', target='fr').translate, original)

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
        await asyncio.sleep(5*60)

# ===================== KEEP ALIVE =====================
async def handle(request):
    return web.Response(text="Bot is alive")

# ===================== MAIN =====================
async def main():
    # Lancer le scheduler
    asyncio.create_task(scheduler_loop())

    # Lancer le serveur web aiohttp
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Server started on port {port}")

    # Boucle infinie pour ne pas quitter
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
