import os
import time
import glob
import threading
import requests
import yt_dlp
from flask import Flask

# 1. خادم ويب وهمي متوافق مع خطة Render المجانية
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7 across all platforms!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. إعدادات التيليجرام
TOKEN = "8721281999:AAGKgK503OTVhv3BCskoCCGeD18ASngNgtw"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(API_URL + "sendMessage", json=payload, timeout=15)
    except Exception as e:
        print("Error sending message:", e)

def send_audio(chat_id, filepath, title):
    try:
        with open(filepath, 'rb') as audio:
            requests.post(
                API_URL + "sendAudio",
                data={"chat_id": chat_id, "title": title[:60]},
                files={"audio": audio},
                timeout=180
            )
    except Exception as e:
        print("Error sending audio:", e)

def send_video(chat_id, filepath, caption):
    try:
        with open(filepath, 'rb') as video:
            requests.post(
                API_URL + "sendVideo",
                data={"chat_id": chat_id, "caption": caption[:100]},
                files={"video": video},
                timeout=180
            )
    except Exception as e:
        print("Error sending video:", e)

user_urls = {}

def process_update(update):
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"].strip()

        if text == "/start":
            send_message(
                chat_id,
                "أهلاً بك! 🚀\n"
                "أرسل رابط أي مقطع من (YouTube, TikTok, Instagram, Facebook, X...) للتحميل مباشرة."
            )
            return

        if not (text.startswith("http://") or text.startswith("https://")):
            send_message(chat_id, "يرجى إرسال رابط صحيح يبدأ بـ http أو https.")
            return

        user_urls[chat_id] = text

        keyboard = {
            "inline_keyboard": [
                [{"text": "🎵 تحميل صوت MP3 / M4A", "callback_data": "audio"}],
                [{"text": "🎬 أعلى جودة متاحة", "callback_data": "res_best"}],
                [{"text": "🎬 جودة متوسطة (720p)", "callback_data": "res_720"}],
                [{"text": "🎬 جودة خفيفة (360p)", "callback_data": "res_360"}]
            ]
        }
        send_message(chat_id, "اختر طريقة التحميل أو الجودة المطلوبة:", reply_markup=keyboard)

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data = query["data"]
        url = user_urls.get(chat_id)

        if not url:
            send_message(chat_id, "انتهت صلاحية الجلسة، يرجى إرسال الرابط مرة أخرى.")
            return

        send_message(chat_id, "جاري استخراج المقطع وتحميله... يرجى الانتظار ⏳")

        os.makedirs("downloads", exist_ok=True)
        out_template = f"downloads/{chat_id}_{int(time.time())}.%(ext)s"

        # إعدادات متوافقة وشاملة لكافة المنصات والحسابات
        ydl_opts = {
            'outtmpl': out_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android']
                }
            }
        }

        if data == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            is_audio = True
        elif data == "res_best":
            ydl_opts['format'] = 'best[ext=mp4]/best'
            is_audio = False
        else:
            height = data.split("_")[1]
            ydl_opts['format'] = f'best[height<={height}][ext=mp4]/best[height<={height}]/best'
            is_audio = False

        downloaded_file = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Media')
                downloaded_file = ydl.prepare_filename(info)

            # التحقق من وجود الملف في المسار المتوقع
            if not os.path.exists(downloaded_file):
                # بحث بديل في المجلد في حال تغيّر الامتداد تلقائياً
                pattern = f"downloads/{chat_id}_*.*"
                matched = glob.glob(pattern)
                if matched:
                    downloaded_file = matched[0]

            if downloaded_file and os.path.exists(downloaded_file):
                file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)

                # تنبيه حد تيليجرام للبوتات (50MB)
                if file_size_mb > 49.5:
                    send_message(
                        chat_id,
                        f"⚠️ حجم الملف ({file_size_mb:.1f} MB) يتجاوز الحد الأقصى المسموح به في تيليجرام للبوتات (50 MB).\n"
                        "يرجى تجربة اختيار جودة أقل."
                    )
                else:
                    send_message(chat_id, "تم التحميل بنجاح! جاري الإرسال إليك... 📤")
                    if is_audio:
                        send_audio(chat_id, downloaded_file, title)
                    else:
                        send_video(chat_id, downloaded_file, title)
            else:
                send_message(chat_id, "تعذر استخراج الملف. يرجى التأكد من أن الرابط عام ومتاح للجميع.")

        except Exception as e:
            err_msg = str(e)
            if "Private video" in err_msg or "login" in err_msg.lower():
                send_message(chat_id, "خطأ: هذا المقطع خاص أو يتطلب تسجيل دخول لمشاهدته.")
            else:
                send_message(chat_id, f"حدث خطأ أثناء المعالجة: {err_msg[:120]}")

        finally:
            # تنظيف السيرفر وحذف الملفات المؤقتة فور الانتهاء
            for f in glob.glob(f"downloads/{chat_id}_*.*"):
                try:
                    os.remove(f)
                except Exception:
                    pass

def run_bot():
    offset = 0
    print("البوت يعمل الآن ومستعد لكافة المنصات...")
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
