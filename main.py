import telebot
import yt_dlp
import os
import re
import time

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    print("خطا: توکن پیدا نشد!")
    exit()

bot = telebot.TeleBot(TOKEN)

def download_tiktok(url):
    if 'vt.tiktok.com' in url:
        import requests
        try:
            r = requests.head(url, allow_redirects=True, timeout=10)
            url = r.url
        except: pass

    if '/photo/' in url:
        raise ValueError("فقط ویدیو!")

    match = re.search(r'/video/(\d+)', url)
    if not match: raise ValueError("لینک نامعتبر!")
    video_id = match.group(1)

    ydl_opts = {
        'outtmpl': f'{video_id}.mp4',
        'format': 'best[height<=720]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://tiktok.com/video/{video_id}"])
        return f"{video_id}.mp4"
    except Exception as e:
        raise ValueError(f"دانلود نشد: {e}")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text)
def reply(m):
    try:
        status = bot.reply_to(m, "در حال دانلود... ⏳")
        file = download_tiktok(m.text)
        size = os.path.getsize(file) / (1024*1024)
        if size > 48:
            os.remove(file)
            bot.edit_message_text("فایل خیلی بزرگه (>48MB)", m.chat.id, status.id)
            return
        with open(file, 'rb') as v:
            bot.send_video(m.chat.id, v, caption=f"دانلود شد! {size:.1f}MB")
        os.remove(file)
        bot.edit_message_text("ارسال شد ✅", m.chat.id, status.id)
    except Exception as e:
        bot.reply_to(m, f"خطا: {e}")

print("ربات روشن شد — منتظر پیام...")
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
        time.sleep(1)
    except Exception as e:
        print(f"اتصال قطع شد: {e} — ۵ ثانیه دیگه...")
        time.sleep(5)
