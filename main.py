import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from yt_dlp import YoutubeDL

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

user_links = {}

def resolve_url_if_needed(url):
    clean_url = url.strip()
    if "facebook.com" in clean_url or "fb.watch" in clean_url:
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response = session.head(clean_url, allow_redirects=True, timeout=10)
            return response.url
        except Exception:
            return clean_url
    return clean_url

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! 🚀\nارسل رابط الفيديو من (يوتيوب، فيسبوك، تيك توك، إنستجرام) واختر الجودة المناسبة لك.")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    raw_url = message.text.strip()
    if not (raw_url.startswith("http://") or raw_url.startswith("https://")):
        bot.reply_to(message, "من فضلك أرسل رابطاً صحيحاً.")
        return

    user_links[message.chat.id] = raw_url

    markup = InlineKeyboardMarkup(row_width=3)
    btn_240 = InlineKeyboardButton("240p ⚡", callback_data="q_240")
    btn_360 = InlineKeyboardButton("360p 📱", callback_data="q_360")
    btn_480 = InlineKeyboardButton("480p 🎬", callback_data="q_480")
    btn_720 = InlineKeyboardButton("720p HD 🌟", callback_data="q_720")
    btn_1080 = InlineKeyboardButton("1080p FHD 🚀", callback_data="q_1080")
    btn_audio = InlineKeyboardButton("🎵 MP3 صوت فقط", callback_data="q_audio")

    markup.add(btn_240, btn_360, btn_480)
    markup.add(btn_720, btn_1080)
    markup.add(btn_audio)

    bot.reply_to(message, "اختر الجودة المطلوبة للتنزيل:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("q_"))
def process_quality_choice(call):
    chat_id = call.message.chat.id
    if chat_id not in user_links:
        bot.answer_callback_query(call.id, "انتهت جلسة الرابط، يرجى إرسال الرابط مجدداً.")
        return

    raw_url = user_links[chat_id]
    quality_choice = call.data.replace("q_", "")

    bot.edit_message_text("⏳ جاري المعالجة والتحميل بالجودة المختارة...", chat_id=chat_id, message_id=call.message.message_id)

    target_url = resolve_url_if_needed(raw_url)
    
    is_audio_only = (quality_choice == "audio")
    file_ext = "mp3" if is_audio_only else "mp4"
    file_path = f"media_{call.message.message_id}.{file_ext}"

    if is_audio_only:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"media_{call.message.message_id}",
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        res = quality_choice
        ydl_opts = {
            'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]/best[height<={res}]/best',
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([target_url])

        if os.path.exists(file_path):
            bot.edit_message_text("⬆️ جاري الرفع إلى التليجرام...", chat_id=chat_id, message_id=call.message.message_id)

            with open(file_path, 'rb') as f:
                if is_audio_only:
                    bot.send_audio(chat_id, f, caption="🎵 ملف الصوت MP3")
                else:
                    bot.send_video(chat_id, f, caption=f"🎬 الفيديو بجودة {quality_choice}p")

            os.remove(file_path)
            bot.delete_message(chat_id, call.message.message_id)
        else:
            bot.reply_to(call.message, "❌ تعذر العثور على الملف بعد التنزيل.")

    except Exception as e:
        bot.reply_to(call.message, "❌ حدث خطأ أثناء التنزيل. حاول اختيار جودة أقل أو رابط آخر.")
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Bot is starting...")
    bot.infinity_polling(skip_pending_updates=True)
