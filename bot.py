
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

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Désactiver warnings SSL pour quotable.io
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
        return f"🌤️ Météo à {CITY} : {desc}, {temp}°C"
    except Exception as e:
        logging.error(f"Erreur récupération météo: {e}")
        return "⚠️ Erreur récupération météo"

async def send_weather():
    msg = get_weather()
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        logging.error(f"Erreur envoi météo: {e}")

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
        url_fr = f"https://newsapi.org/v2/top-headlines?language=fr&pageSize=15&apiKey={NEWS_API_KEY}"
        new_articles.extend(requests.get(url_fr, timeout=10).json().get("articles", []))

        # EN catégories health, science, technology
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

            msg = f"📰 {title}\n{desc}\n{link}"

            try:
                if img:
                    await bot.send_photo(chat_id=CHAT_ID, photo=img, caption=msg[:1000])
                else:
                    await bot.send_message(chat_id=CHAT_ID, text=msg[:4000])
                sent_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Erreur envoi news: {e}")

        save_seen(seen)

        if sent_count == 0:
            await bot.send_message(chat_id=CHAT_ID, text="📰 Pas de nouvelles inédites")

    except Exception as e:
        logging.error(f"Erreur récupération news: {e}")
        await bot.send_message(chat_id=CHAT_ID, text="⚠️ Erreur récupération news")

# ===================== CITATIONS =====================
async def send_quote():
    for attempt in range(1, 4):  # 3 essais
        try:
            logging.info(f"Essai {attempt} récupération citation...")
            r = requests.get("https://api.quotable.io/random", timeout=15)
            logging.info(f"Status code API quotable: {r.status_code}")
            
            # Vérifier si la réponse est OK
            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}")
            
            data = r.json()
            content = data.get("content")
            author = data.get("author", "Inconnu")
            
            if content:
                msg = f"💡 Citation : {content} — {author}"
                await bot.send_message(chat_id=CHAT_ID, text=msg)
                logging.info("Citation envoyée avec succès")
                return
            else:
                logging.warning(f"Réponse API vide ou invalide (essai {attempt})")
                await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Pas de contenu reçu (essai {attempt})")
                
        except Exception as e:
            logging.error(f"Erreur récupération citation (essai {attempt}): {e}")
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Erreur citation (essai {attempt}): {e}")
            await asyncio.sleep(2)  # pause avant le prochain essai

    # Fallback si tous les essais échouent
    await bot.send_message(chat_id=CHAT_ID, text="⚠️ Erreur récupération citation (API inaccessible après 3 essais)")
    logging.error("Échec récupération citation après 3 essais")

# ===================== SCHEDULER =====================
async def scheduler_loop():
    # Première exécution immédiate + boucle toutes les 30min
    while True:
        await asyncio.gather(send_weather(), send_news(), send_quote())
        await asyncio.sleep(30*60)  # toutes les 30 min

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
    # Flask en thread pour keep-alive
    Thread(target=run_flask).start()
    # Scheduler asyncio loop infinie
    asyncio.get_event_loop().create_task(scheduler_loop())
    asyncio.get_event_loop().run_forever()
