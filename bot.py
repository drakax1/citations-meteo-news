
import requests
import schedule
import time
from datetime import datetime, timedelta
from telegram import Bot
from flask import Flask
from threading import Thread

# === CONFIGURATION EN DUR ===
TOKEN = "8076882358:AAH1inJqY_tJfWOj-7psO3IOqN_X4plI1fE"
CHAT_ID = 7116219655
OWM_API_KEY = "2754828f53424769b54b440f1253486e"
NEWS_API_KEY = "57e9a76a7efa4e238fc9af6a330f790e"
CITY = "Sion,CH"

bot = Bot(token=TOKEN)

# ===================== MÉTÉO =====================
def get_weather():
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OWM_API_KEY}&units=metric&lang=fr"
    r = requests.get(url).json()
    desc = r['weather'][0]['description']
    temp = r['main']['temp']
    return f"🌤️ Météo à {CITY} : {desc}, {temp}°C"

def get_alerts():
    url = f"https://api.openweathermap.org/data/2.5/onecall?lat=46.233&lon=7.366&appid={OWM_API_KEY}&lang=fr"
    r = requests.get(url).json()
    if "alerts" in r:
        alerts = [a['description'] for a in r['alerts']]
        return "\n⚠️ ALERTE MÉTÉO :\n" + "\n".join(alerts)
    return None

def send_weather():
    msg = get_weather()
    bot.send_message(chat_id=CHAT_ID, text=msg)
    alert = get_alerts()
    if alert:
        bot.send_message(chat_id=CHAT_ID, text=alert)

# ===================== NEWS =====================
def get_news():
    now = datetime.utcnow()
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
    return "📰 Dernières actus :\n" + "\n".join([a['title'] for a in articles])

def send_news():
    msg = get_news()
    bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== CITATIONS =====================
def get_quote():
    r = requests.get("https://api.quotable.io/random")
    data = r.json()
    return f"💡 Citation : {data['content']} — {data['author']}"

def send_quote():
    msg = get_quote()
    bot.send_message(chat_id=CHAT_ID, text=msg)

# ===================== PLANIFICATION =====================
schedule.every().hour.at(":00").do(send_weather)
schedule.every().hour.at(":05").do(send_news)
schedule.every().hour.at(":10").do(send_quote)

# ===================== KEEP ALIVE POUR RENDER =====================
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===================== BOUCLE PRINCIPALE =====================
if __name__ == "__main__":
    keep_alive()
    while True:
        schedule.run_pending()
        time.sleep(30)
