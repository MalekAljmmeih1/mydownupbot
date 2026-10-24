import os
import time
import threading
import requests
import yt_dlp
from flask import Flask

# سيرفر ويب وهمي لتشغيل البوت مجاناً على Render دون توقف
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# إعدادات بوت تلجرام
TOKEN = "8721281999:AAGKgK503OTVhv3BCskoCCGeD18ASngNgtw"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(API_URL + "sendMessage", json=payload, timeout=10)
    except Exception as e:
        print("Error sending message:", e)

def send_audio(chat_id, filepath, title):
    try:
        with open(filepath, 'rb') as audio:
            requests.post(API_URL + "sendAudio", data={"chat_id": chat_id, "title": title}, files={"audio": audio}, timeout=120)
    except Exception as e:
        print("Error sending audio:", e)

def send_video(chat_id, filepath, caption):
    try:
        with open(filepath, 'rb') as video:
            requests.post(API_URL + "sendVideo", data={"chat_id": chat_id, "caption": caption}, files={"video": video}, timeout=120)
    except Exception as e:
        print("Error sending video:", e)

user_urls = {}

def process_update(update):
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"].strip()

        if text == "/start":
            send_message(chat_id, "أهلاً بك في mydownupbot! 🚀\nأرسل لي رابط أي فيديو وسأقدم لك خيارات التنزيل المتاحة.")
            return

        if not text.startswith("http"):
            send_message(chat_id, "يرجى إرسال رابط صحيح يبدأ بـ http أو https.")
            return

        user_urls[chat_id] = text

        keyboard = {
            "inline_keyboard": [
                [{"text": "🎵 تحميل صوت MP3", "callback_data": "audio_mp3"}],
                [{"text": "🎬 1080p", "callback_data": "res_1080"}, {"text": "🎬 720p", "callback_data": "res_720"}],
                [{"text": "🎬 480p", "callback_data": "res_480"}, {"text": "🎬 360p", "callback_data": "res_360"}]
            ]
        }
        send_message(chat_id, "اختر جودة التنزيل المطلوبة أو تحويل إلى صوت MP3:", reply_markup=keyboard)

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data = query["data"]
        url = user_urls.get(chat_id)

        if not url:
            send_message(chat_id, "عذراً، انتهت صلاحية الجلسة. أرسل الرابط مرة أخرى.")
            return

        send_message(chat_id, "جاري المعالجة والتحميل... انتظر لحظة ⏳")

        if data == "audio_mp3":
            ydl_opts = {'format': 'bestaudio/best', 'outtmpl': f'downloads/{chat_id}_%(title)s.%(ext)s'}
            is_audio = True
        else:
            res = data.split("_")[1]
            ydl_opts = {'format': f'bestvideo[height<={res}]+bestaudio/best[height<={res}]/best', 'outtmpl': f'downloads/{chat_id}_%(title)s.%(ext)s'}
            is_audio = False

        try:
            os.makedirs("downloads", exist_ok=True)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            send_message(chat_id, "جاري رفع الملف إليك... 📤")

            if is_audio:
                send_audio(chat_id, filename, info.get('title', 'Audio'))
            else:
                send_video(chat_id, filename, info.get('title', 'Video'))

            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            send_message(chat_id, f"حدث خطأ أثناء التنزيل: {e}")

def run_bot():
    offset = 0
    print("البوت يعمل بنجاح 24/7...")
    while True:
        try:
            r = requests.get(API_URL + f"getUpdates?offset={offset}&timeout=10", timeout=15)
            if r.status_code == 200:
                data = r.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    process_update(update)
        except Exception:
            pass
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    run_web()
