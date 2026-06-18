import asyncio
import requests
import qrcode
import io
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'
OPENROUTER_API_KEY = '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'
GOLD_API_KEY = 'goldapi-615dd989f010af41bbde17b0213d7075-io'
AI_MODEL = 'qwen/qwen3-coder:free'

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

user_states = {}
user_chat_history = {}

def get_prices():
    try:
        headers = {"x-access-token": GOLD_API_KEY, "Content-Type": "application/json"}
        
        gold_response = requests.get("https://www.goldapi.io/api/XAU/USD", headers=headers, timeout=10)
        gold_data = gold_response.json()
        gold_ons_usd = gold_data['price']
        
        silver_response = requests.get("https://www.goldapi.io/api/XAG/USD", headers=headers, timeout=10)
        silver_data = silver_response.json()
        silver_ons_usd = silver_data['price']
        
        currency_url = "https://api.exchangerate-api.com/v4/latest/USD"
        currency_response = requests.get(currency_url, timeout=10)
        currency_data = currency_response.json()
        usd_try = currency_data['rates']['TRY']
        
        gold_gram_usd = gold_ons_usd / 31.1035
        silver_gram_usd = silver_ons_usd / 31.1035
        
        gold_gram_try = round(gold_gram_usd * usd_try, 2)
        silver_gram_try = round(silver_gram_usd * usd_try, 2)
        
        return {
            'gold_gram': gold_gram_try,
            'silver_gram': silver_gram_try,
            'usd_try': round(usd_try, 2),
            'gold_ons': round(gold_ons_usd, 2),
            'silver_ons': round(silver_ons_usd, 2)
        }
    except Exception as e:
        print("Fiyat hatasi:", e)
        return None

def shorten_link(url):
    try:
        response = requests.get("https://is.gd/create.php?format=simple&url=" + url, timeout=10)
        if response.status_code == 200:
            return response.text.strip()
        return url
    except:
        return url

def create_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    bio.name = 'qrcode.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

def ask_ai(user_id, message):
    try:
        if user_id not in user_chat_history:
            user_chat_history[user_id] = []
        
        user_chat_history[user_id].append({"role": "user", "content": message})
        
        if len(user_chat_history[user_id]) > 10:
            user_chat_history[user_id] = user_chat_history[user_id][-10:]
        
        headers = {
            "Authorization": "Bearer " + OPENROUTER_API_KEY,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/fettahciftci/telegram-bot",
            "X-Title": "Telegram Bot"
        }
        
        data = {
            "model": AI_MODEL,
            "messages": user_chat_history[user_id]
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_message = result['choices'][0]['message']['content']
            user_chat_history[user_id].append({"role": "assistant", "content": ai_message})
            return ai_message
        else:
            return "AI yanit veremedi. Hata: " + str(response.status_code)
    except Exception as e:
        return "AI hatasi: " + str(e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Altin Gram (TL)", callback_data='gold')],
        [InlineKeyboardButton("Gumus Gram (TL)", callback_data='silver')],
        [InlineKeyboardButton("Hesapla (Gram -> TL)", callback_data='calc')],
        [InlineKeyboardButton("QR Kod Olustur", callback_data='qr')],
        [InlineKeyboardButton("Link Kisalt", callback_data='shorten')],
        [InlineKeyboardButton("AI Sohbet (Qwen3)", callback_data='ai_chat')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Altin & Gumus Bot + AI\n\nBir buton sec:',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == 'gold':
        prices = get_prices()
        if prices:
            msg = "ALTI GRAM FIYATI (GÜNCEL)\n\n"
            msg += "USD/TRY: " + str(prices['usd_try']) + " TL\n"
            msg += "Altin Ons: $" + str(prices['gold_ons']) + "\n"
            msg += "1 Gram Altin: " + str(prices['gold_gram']) + " TL\n\n"
            msg += "Kaynak: GoldAPI.io"
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("Fiyat bilgisi alinamadi. GoldAPI key kontrol et.")
    
    elif data == 'silver':
        prices = get_prices()
        if prices:
            msg = "GUMUS GRAM FIYATI (GÜNCEL)\n\n"
            msg += "USD/TRY: " + str(prices['usd_try']) + " TL\n"
            msg += "Gumus Ons: $" + str(prices['silver_ons']) + "\n"
            msg += "1 Gram Gumus: " + str(prices['silver_gram']) + " TL\n\n"
            msg += "Kaynak: GoldAPI.io"
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("Fiyat bilgisi alinamadi. GoldAPI key kontrol et.")
    
    elif data == 'calc':
        user_states[user_id] = 'waiting_calc'
        await query.edit_message_text(
            "HESAPLAMA MODU\n\n"
            "Kac gram hesaplamak istiyorsun?\n"
            "Ornek: 5\n\n"
            "Gram miktarini yaz:"
        )
    
    elif data == 'qr':
        user_states[user_id] = 'waiting_qr'
        await query.edit_message_text(
            "QR KOD OLUSTURUCU\n\n"
            "QR kod yapmak istedigin linki gonder:\n"
            "Ornek: https://example.com"
        )
    
    elif data == 'shorten':
        user_states[user_id] = 'waiting_shorten'
        await query.edit_message_text(
            "LINK KISALTICI\n\n"
            "Kisaltmak istedigin linki gonder:\n"
            "Ornek: https://example.com/cok-uzun-link"
        )
    
    elif data == 'ai_chat':
        user_states[user_id] = 'waiting_ai'
        await query.edit_message_text(
            "AI SOHBET (Qwen3 Coder)\n\n"
            "Artik AI ile sohbet edebilirsin!\n"
            "Sorularini yaz, cevap verecek.\n\n"
            "Cikmak icin /start yaz."
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if state == 'waiting_calc':
        try:
            gram = float(text)
            prices = get_prices()
            if prices:
                gold_total = gram * prices['gold_gram']
                silver_total = gram * prices['silver_gram']
                msg = "HESAPLAMA SONUCU\n\n"
                msg += "Gram: " + str(gram) + "g\n\n"
                msg += "Altin: " + str(round(gold_total, 2)) + " TL\n"
                msg += "Gumus: " + str(round(silver_total, 2)) + " TL\n\n"
                msg += "Fiyatlar güncel (GoldAPI.io)"
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text("Fiyat bilgisi alinamadi.")
        except ValueError:
            await update.message.reply_text("Gecersiz sayi. Lutfen bir sayi gir (orn: 5)")
        del user_states[user_id]
    
    elif state == 'waiting_qr':
        try:
            bio = create_qr(text)
            await update.message.reply_photo(photo=bio, caption="QR Kod:\n" + text)
        except Exception as e:
            await update.message.reply_text("QR kod olusturulamadi: " + str(e))
        del user_states[user_id]
    
    elif state == 'waiting_shorten':
        try:
            short_url = shorten_link(text)
            msg = "LINK KISALTILDI\n\n"
            msg += "Orijinal: " + text + "\n"
            msg += "Kisa: " + short_url
            await update.message.reply_text(msg)
        except Exception as e:
            await update.message.reply_text("Link kisaltilamadi: " + str(e))
        del user_states[user_id]
    
    elif state == 'waiting_ai':
        await update.message.reply_text("AI dusunuyor...")
        response = ask_ai(user_id, text)
        
        if len(response) > 4000:
            response = response[:4000] + "\n\n[Devami kesildi...]"
        
        await update.message.reply_text(response)

async def run_bot():
    print('Bot baslatiliyor...')
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print('Bot aktif!')
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    while True:
        await asyncio.sleep(1)

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    Thread(target=run_flask, daemon=True).start()
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        print('Bot kapandi')
    finally:
        loop.close()

if __name__ == '__main__':
    main()
