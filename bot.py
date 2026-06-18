import asyncio
import requests
import qrcode
import io
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'

# Flask web sunucusu
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Bot 7/24 çalışıyor!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# Kullanıcı durumlarını takip et
user_states = {}

# Gerçek fiyatları al (TL olarak)
def get_prices():
    try:
        # Ücretsiz API (TL bazlı)
        url = "https://api.exchangerate-api.com/v4/latest/TRY"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Altın ve gümüş fiyatları (ons/gram dönüşümü)
        # 1 ons = 31.1035 gram
        usd_try = data['rates']['USD']
        
        # Yaklaşık gram fiyatları (gerçek zamanlı değil, örnek)
        gold_try_gram = usd_try * 75.5  # 1 gram altın yaklaşık $75.5
        silver_try_gram = usd_try * 0.95  # 1 gram gümüş yaklaşık $0.95
        
        return {
            'gold_gram': round(gold_try_gram, 2),
            'silver_gram': round(silver_try_gram, 2),
            'usd_try': round(usd_try, 2)
        }
    except Exception as e:
        return None

# Link kısaltma
def shorten_link(url):
    try:
        response = requests.get(f"https://is.gd/create.php?format=simple&url={url}", timeout=10)
        if response.status_code == 200:
            return response.text
        return url
    except:
        return url

# QR kod oluştur
def create_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # BytesIO'ya kaydet
    bio = io.BytesIO()
    bio.name = 'qrcode.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🥇 Altın Gram (TL)", callback_data='gold')],
        [InlineKeyboardButton("🥈 Gümüş Gram (TL)", callback_data='silver')],
        [InlineKeyboardButton("💰 Hesapla (Gram → TL)", callback_data='calc')],
        [InlineKeyboardButton("📱 QR Kod Oluştur", callback_data='qr')],
        [InlineKeyboardButton("🔗 Link Kısalt", callback_data='shorten')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '💰 *Altın & Gümüş Bot*\n\n'
        'Aşağıdaki butonlardan birini seç:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Buton tıklama handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'gold':
        prices = get_prices()
        if prices:
            await query.edit_message_text(
                f"🥇 *Altın Gram Fiyatı*\n\n"
                f"💵 USD/TRY: {prices['usd_try']}₺\n"
                f"🏆 1 Gram Altın: {prices['gold_gram']}₺\n\n"
                f"⚠️ Fiyatlar yaklaşık değerlerdir.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Fiyat bilgisi alınamadı. Lütfen tekrar dene.")
    
    elif data == 'silver':
        prices = get_prices()
        if prices:
            await query.edit_message_text(
                f"🥈 *Gümüş Gram Fiyatı*\n\n"
                f"💵 USD/TRY: {prices['usd_try']}₺\n"
                f"🥈 1 Gram Gümüş: {prices['silver_gram']}₺\n\n"
                f"⚠️ Fiyatlar yaklaşık değerlerdir.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Fiyat bilgisi alınamadı. Lütfen tekrar dene.")
    
    elif data == 'calc':
        user_states[query.from_user.id] = 'waiting_calc'
        await query.edit_message_text(
            "💰 *Hesaplama Modu*\n\n"
            "Kaç gram altın/gümüş hesaplamak istiyorsun?\n"
            "Örnek: `5` (5 gram için)\n\n"
            "Hesaplamak istediğin gram miktarını yaz:",
            parse_mode='Markdown'
        )
    
    elif data == 'qr':
        user_states[query.from_user.id] = 'waiting_qr'
        await query.edit_message_text(
            "📱 *QR Kod Oluşturucu*\n\n"
            "QR kod oluşturmak istediğin linki gönder:\n"
            "Örnek: `https://example.com`",
            parse_mode='Markdown'
        )
    
    elif data == 'shorten':
        user_states[query.from_user.id] = 'waiting_shorten'
        await query.edit_message_text(
            "🔗 *Link Kısaltıcı*\n\n"
            "Kısaltmak istediğin linki gönder:\n"
            "Örnek: `https://example.com/very-long-url`",
            parse_mode='Markdown'
        )

# Mesaj handler (kullanıcı inputları için)
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
                
                await update.message.reply_text(
                    f"💰 *Hesaplama Sonucu*\n\n"
                    f"📊 Gram: {gram}g\n\n"
                    f"🥇 Altın: {gold_total:,.2f}₺\n"
                    f"🥈 Gümüş: {silver_total:,.2f}
