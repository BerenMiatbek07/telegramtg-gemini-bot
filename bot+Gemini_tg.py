import telebot
import scrapetube
import schedule
import time
from langdetect import detect
import google.generativeai as genai
from pytube import YouTube
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Бот конфигурациясы (TOKEN-ді өзіңіздікісін қою керек)
BOT_TOKEN = '8178504281:AAEP3XgJih0wTccf8bqme-GOhSEPXvE9hbY'
CHANNEL_USERNAME = '@BM_Films07'
COMMENT_CHAT_ID = -1001627971823
GEMINI_API_KEY = 'AIzaSyBUJhu-xpB-Dewo01oiZfPYv1RKyM8_TQ4'

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)  # TeleBot объектісін құру13
genai.configure(api_key=GEMINI_API_KEY)  # Google Gemini API кілтін конфигурациялау14

# YouTube-дан соңғы видеоны бақылау айнымалысы
last_video_id = None

def check_youtube_new_video():
    global last_video_id
    channel_id = "UCxlWZOOwrSrtlvPiDlmmw8A"
    # Арнадағы жаңа видеоны алу (ең соңғы жаңарылған)15
    videos = scrapetube.get_channel(channel_id, sort_by="newest")
    try:
        latest_video = next(videos)
    except StopIteration:
        return
    vid_id = latest_video.get('videoId')
    if vid_id and vid_id != last_video_id:
        # Жаңа видео табылды
        last_video_id = vid_id
        url = f"https://www.youtube.com/watch?v={vid_id}"
        # Видео тақырыбын алу үшін pytube пайдалану
        try:
            yt = YouTube(url)
            title = yt.title
        except Exception:
            title = "Жаңа видео"
        text = f"🎬 Жаңа видео шықты: *{title}*\n{url}"
        bot.send_message(CHANNEL_USERNAME, text)  # Арнаға хабарлама жіберу16

# Әр 2 сағат сайын көңілді кино тақырыбындағы мәтін генерациялау
def scheduled_post():
    prompt = "Киноға қатысты көңілді әрі қызықты мәтін жазыңыз (қазақ тілінде)."
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)  # Gemini-ге сұрау жіберу17
    text = response.text.strip()
    bot.send_message(CHANNEL_USERNAME, text)  # Нәтижені арнаға жариялау

# Комментарий чатындағы хабарламаға жауап беру және қара тізім тексеру
warnings = {}  # Қолданушыға ескерту саны сақталатын dict: {user_id: count}

@bot.message_handler(func=lambda m: m.chat.id == COMMENT_CHAT_ID, content_types=['text'])
def handle_comment_message(message):
    user_id = message.from_user.id
    text = message.text.lower()
    # Боқтық сөздерді тексеру (қарапайым мысал сөздер)
    kazakh_profanity = ["қотақ", "ам", "қаншық", "шешең", "сора", "далбаёб"]
    russian_profanity = ["сука", "блядь", "хуй", "пизда", "гандон"]  # Қажет болса нақты сөздерді қосыңыз
     # Мысалға ағылшын сөздері, нақты орысша сөздермен ауыстырыңыз
    # Қазақша анықтау: мәтінде қазақ әріптері бар ма?
    language = 'ru'
    if detect(text) == 'ru':
        language = 'ru'
    elif any(ch in text for ch in "әғқңөүі"):
        language = 'kk'
    # Боқтық сөздерді қарастыру
    if any(word in text for word in kazakh_profanity):
        warnings[user_id] = warnings.get(user_id, 0) + 1
        if warnings[user_id] >= 3:
            bot.kick_chat_member(COMMENT_CHAT_ID, user_id)  # 3 ескерту: чаттан шығару
            return
        else:
            bot.reply_to(message, f"Ескерту: ұят сөз қолданбаңыз! ({warnings[user_id]}/3)")

    # Gemini арқылы жауап генерациялау
    reply_prompt = ""
    if language == 'ru':
        reply_prompt = f"Мысалы, жауап ретінде әзілдейтін және түсінікті түрде орыс тілінде жауап бер: {text}"
    else:
        reply_prompt = f"Кінәммен Қазақстан киносы туралы қызықты жауап бер: {text}"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(reply_prompt)
        reply = response.text.strip()
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "Кешіріңіз, қате болды, кейінірек қайта сұраңыз.")

# Алғашқы тексерісті бір рет жасау
check_youtube_new_video()

# Кестеге салып жұмыс істеу: әр екі сағат сайын функцияларды шақыру18
schedule.every(2).hours.do(check_youtube_new_video)
schedule.every(2).hours.do(scheduled_post)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

# Фондық кестені іске қосу (кейбірінтернет-сервистерде үшінші тарап әдістері қажет)
import threading
threading.Thread(target=run_schedule, daemon=True).start()

# Ботты іске қосу (жұмысын үздіксіз жасау үшін)
# Ботты іске қосу
keep_alive()  # Бұл өте маңызды! Render Flask портына қарап тұрады!
bot.infinity_polling()
