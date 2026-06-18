import asyncio
import requests
import qrcode
import io
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

user_states = {}

def get_prices():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        usd_try = data['rates']['TRY']
        gold_gram = round(usd_try * 75.5, 2)
        silver_gram = round(usd_try * 0.95, 2)
        return {
            'gold_gram': gold_gram,
            'silver_gram': silver_gram,
            'usd_try': round(usd_try, 2)
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Altin Gram (TL)", callback_data='gold')],
        [InlineKeyboardButton("Gumus Gram (TL)", callback_data='silver')],
        [InlineKeyboardButton("Hesapla (Gram -> TL)", callback_data='calc')],
        [InlineKeyboardButton("QR Kod Olustur", callback_data='qr')],
        [InlineKeyboardButton("Link Kisalt", callback_data='shorten')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Altin & Gumus Bot\n\nBir buton sec:',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'gold':
        prices = get_prices()
        if prices:
            msg = "ALTI GRAM FIYATI\n\n"
            msg += "USD/TRY: " + str(prices['usd_try']) + "\n"
            msg += "1 Gram Altin: " + str(prices['gold_gram']) + " TL\n\n"
            msg += "Fiyatlar yaklasik degerlerdir."
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("Fiyat bilgisi alinamadi.")
    
    elif data == 'silver':
        prices = get_prices()
        if prices:
            msg = "GUMUS GRAM FIYATI\n\n"
            msg += "USD/TRY: " + str(prices['usd_try']) + "\n"
            msg += "1 Gram Gumus: " + str(prices['silver_gram']) + " TL\n\n"
            msg += "Fiyatlar yaklasik degerlerdir."
            await query.edit_message_text(msg)
        else:
            await query.edit_message_text("Fiyat bilgisi alinamadi.")
    
    elif data == 'calc':
        user_states[query.from_user.id] = 'waiting_calc'
        await query.edit_message_text(
            "HESAPLAMA MODU\n\n"
            "Kac gram hesaplamak istiyorsun?\n"
            "Ornek: 5\n\n"
            "Gram miktarini yaz:"
        )
    
    elif data == 'qr':
        user_states[query.from_user.id] = 'waiting_qr'
        await query.edit_message_text(
            "QR KOD OLUSTURUCU\n\n"
            "QR kod yapmak istedigin linki gonder:\n"
            "Ornek: https://example.com"
        )
    
    elif data == 'shorten':
        user_states[query.from_user.id] = 'waiting_shorten'
        await query.edit_message_text(
            "LINK KISALTICI\n\n"
            "Kisaltmak istedigin linki gonder:\n"
            "Ornek: https://example.com/cok-uzun-link"
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
                msg += "Fiyatlar yaklasik degerlerdir."
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
            msg = "
