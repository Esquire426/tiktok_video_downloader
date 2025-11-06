import telebot
import yt_dlp
import os
import re

# توکن ربات
TOKEN = 'your token'  # عوضش کن!
bot = telebot.TeleBot(TOKEN)

def download_tiktok(url):
    # تبدیل لینک کوتاه vt.tiktok.com
    if 'vt.tiktok.com' in url:
        try:
            import requests
            response = requests.head(url, allow_redirects=True, timeout=10)
            url = response.url
        except:
            pass

    # فقط ویدیوها رو قبول کن
    if '/photo/' in url:
        raise ValueError("فقط ویدیو! عکس اسلایدی پشتیبانی نمی‌شه.")

    # استخراج آیدی
    match = re.search(r'/video/(\d+)', url)
    if not match:
        raise ValueError("لینک ویدیو نامعتبر!")
    video_id = match.group(1)
    clean_url = f"https://www.tiktok.com/@/video/{video_id}"

    ydl_opts = {
        'outtmpl': f'{video_id}.%(ext)s',
        'format': 'best[height<=720][ext=mp4]/best[height<=720]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'retries': 5,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base = filename.rsplit('.', 1)[0]
                for ext in ['.mp4', '.webm']:
                    test = base + '.' + ext
                    if os.path.exists(test):
                        filename = test
                        break
            return filename
    except Exception as e:
        print(f"خطا در دانلود: {e}")
        raise ValueError("دانلود نشد.")

@bot.message_handler(func=lambda m: True)
def reply(message):
    if 'tiktok.com' not in message.text:
        return

    try:
        status_msg = bot.send_message(message.chat.id, "در حال دانلود... ⏳")

        if message.chat.type in ['group', 'supergroup']:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass

        file_path = download_tiktok(message.text)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        if file_size_mb > 48:
            os.remove(file_path)
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text="فایل خیلی بزرگه (>50 مگ)!"
            )
            return

        with open(file_path, 'rb') as f:
            bot.send_video(
                message.chat.id,
                f,
                caption=f"دانلود شد!\nحجم: {file_size_mb:.1f} مگ",
                timeout=1200
            )

        os.remove(file_path)

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text="ارسال شد ✅"
        )

    except Exception as e:
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=f"خطا: {str(e)}"
            )
        except:
            pass

print("ربات روشن شد...")
bot.polling()