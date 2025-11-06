import telebot
import yt_dlp
import os
import re
import time
import logging

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    print("خطا: توکن پیدا نشد!")
    exit()

bot = telebot.TeleBot(TOKEN)

def extract_tiktok_url(text):
    # پیدا کردن هر لینک تیک‌تاک
    urls = re.findall(r'(https?://[^\s]+tiktok\.com/[^\s]+)', text)
    for url in urls:
        url = url.split('?')[0]  # حذف پارامترها
        if '/video/' in url or 'vt.tiktok.com' in url:
            return url
    return None

def download_tiktok(url):
    # حل مشکل ریدایرکت vt.tiktok.com
    if 'vt.tiktok.com' in url:
        import requests
        try:
            with requests.Session() as s:
                s.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                r = s.head(url, allow_redirects=True, timeout=15)
                url = r.url
        except Exception as e:
            print(f"ریدایرکت شکست: {e}")

    # چک کردن 404
    if 'tiktok.com/404' in url:
        raise ValueError("لینک منقضی شده یا نامعتبر است.")

    # فقط ویدیو
    if '/photo/' in url:
        raise ValueError("فقط ویدیو!")

    # استخراج ID
    match = re.search(r'/video/(\d+)', url)
    if not match:
        raise ValueError("لینک ویدیو پیدا نشد!")
    video_id = match.group(1)

    ydl_opts = {
        'outtmpl': f'{video_id}.mp4',
        'format': 'best[height<=720][ext=mp4]/best[height<=720]/best',
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'cookiefile': 'cookies.txt',  # اختیاری: اگر کوکی داری
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'retries': 3,
        'fragment_retries': 5,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        raise ValueError(f"دانلود نشد: {str(e)}")

@bot.message_handler(func=lambda m: 'tiktok.com' in m.text.lower())
def reply(m):
    try:
        url = extract_tiktok_url(m.text)
        if not url:
            bot.reply_to(m, "لینک تیک‌تاک پیدا نشد!")
            return

        status = bot.reply_to(m, "در حال دانلود... ⏳")

        file_path = download_tiktok(url)
        if not os.path.exists(file_path):
            raise ValueError("فایل دانلود نشد.")

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 48:
            os.remove(file_path)
            bot.edit_message_text("فایل خیلی بزرگه (>48MB)", m.chat.id, status.id)
            return

        with open(file_path, 'rb') as video:
            bot.send_video(
                m.chat.id,
                video,
                caption=f"دانلود شد! {size_mb:.1f}MB",
                reply_to_message_id=m.message_id
            )

        os.remove(file_path)
        bot.edit_message_text("ارسال شد ✅", m.chat.id, status.id)

    except Exception as e:
        error_msg = str(e)
        if "Private video" in error_msg:
            error_msg = "ویدیو خصوصی است!"
        elif "Video unavailable" in error_msg:
            error_msg = "ویدیو در دسترس نیست!"
        bot.edit_message_text(f"خطا: {error_msg}", m.chat.id, status.id)

print("ربات روشن شد — منتظر پیام...")
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"اتصال قطع شد: {e} — ۵ ثانیه دیگه...")
        time.sleep(5)
