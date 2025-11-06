import telebot
import yt_dlp
import os
import re
import time
import logging
import requests

# لاگ برای دیباگ
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    print("خطا: توکن پیدا نشد!")
    exit()

bot = telebot.TeleBot(TOKEN)

# استخراج لینک تیک‌تاک
def extract_tiktok_url(text):
    urls = re.findall(r'(https?://[^\s]+tiktok\.com/[^\s]+)', text)
    for url in urls:
        url = url.split('?')[0]
        if '/video/' in url or 'vt.tiktok.com' in url:
            return url
    return None

# ارسال ویدیو با requests
def send_video_telegram(chat_id, file_path, caption, reply_to_message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    with open(file_path, 'rb') as video:
move        files = {'video': video}
        data = {
            'chat_id': chat_id,
            'caption': caption,
            'reply_to_message_id': reply_to_message_id
        }
        for i in range(3):
            try:
                response = requests.post(url, data=data, files=files, timeout=120)
                result = response.json()
                if result.get('ok'):
                    return True
                else:
                    print("تلگرام خطا داد:", result)
            except Exception as e:
                print(f"تلگرام ارسال ناموفق (تلاش {i+1}): {e}")
                if i == 2:
                    return False
                time.sleep(3)
    return False

# دانلود ویدیو
def download_tiktok(url):
    if 'vt.tiktok.com' in url:
        try:
            with requests.Session() as s:
                s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                r = s.head(url, allow_redirects=True, timeout=15)
                url = r.url
        except Exception as e:
            print(f"ریدایرکت شکست: {e}")

    if 'tiktok.com/404' in url:
        raise ValueError("لینک منقضی شده یا نامعتبر است.")

    if '/photo/' in url:
        raise ValueError("فقط ویدیو!")

    match = re.search(r'/video/(\d+)', url)
    if not match:
        raise ValueError("لینک ویدیو پیدا نشد!")
    video_id = match.group(1)

    ydl_opts = {
        'outtmpl': f'{video_id}.mp4',
        'format': 'best[height<=720][ext=mp4]/best[height<=720]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': False,
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
        'retries': 5,
        'fragment_retries': 10,
        'socket_timeout': 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        raise ValueError(f"دانلود نشد: {str(e)}")

# هندلر پیام
@bot.message_handler(func=lambda m: 'tiktok.com' in m.text.lower())
def reply(m):
    file_path = None
    status_msg = None
    try:
        url = extract_tiktok_url(m.text)
        if not url:
            bot.reply_to(m, "لینک تیک‌تاک پیدا نشد!")
            return

        status_msg = bot.reply_to(m, "در حال دانلود... ⏳")
        print(f"وضعیت پیام: {status_msg.message_id} | کاربر: {m.message_id}")

        file_path = download_tiktok(url)
        if not os.path.exists(file_path):
            raise ValueError("فایل دانلود نشد.")

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 48:
            raise ValueError("فایل خیلی بزرگه (>48MB)")

        if send_video_telegram(m.chat.id, file_path, f"دانلود شد! {size_mb:.1f}MB", m.message_id):
            # پاک کردن پیام کاربر
            try:
                bot.delete_message(m.chat.id, m.message_id)
                print(f"پیام کاربر پاک شد: {m.message_id}")
            except Exception as e:
                print(f"خطا در پاک کردن پیام کاربر: {e}")

            # پاک کردن پیام وضعیت
            try:
                bot.delete_message(m.chat.id, status_msg.message_id)
                print(f"پیام وضعیت پاک شد: {status_msg.message_id}")
            except Exception as e:
                print(f"خطا در پاک کردن پیام وضعیت: {e}")

            bot.send_message(m.chat.id, "ویدیو با موفقیت ارسال شد! ✅")
        else:
            raise Exception("ارسال به تلگرام ناموفق بود.")

    except Exception as e:
        error_msg = str(e)
        if "Private video" in error_msg:
            error_msg = "ویدیو خصوصی است!"
        elif "Video unavailable" in error_msg:
            error_msg = "ویدیو در دسترس نیست!"
        elif "منقضی" in error_msg or "404" in error_msg:
            error_msg = "لینک منقضی شده یا نامعتبر است."
        elif "بزرگه" in error_msg:
            error_msg = "فایل خیلی بزرگه (>48MB)"

        try:
            if status_msg:
                bot.edit_message_text(f"خطا: {error_msg}", m.chat.id, status_msg.message_id)
        except:
            try:
                bot.reply_to(m, f"خطا: {error_msg}")
            except:
                pass

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"فایل پاک شد: {file_path}")
            except Exception as e:
                print(f"خطا در پاک کردن فایل: {e}")

# تست ساده
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "ربات فعال است! لینک تیک‌تاک بفرستید.")
    print(f"کاربر {m.from_user.id} دستور /start داد")

# اجرای ربات
if __name__ == '__main__':
    print("ربات روشن شد — منتظر پیام...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=30)
        except Exception as e:
            print(f"Polling قطع شد: {e}")
            time.sleep(5)
