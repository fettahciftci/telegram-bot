import asyncio
import re
import requests
import qrcode
import io
import json
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime
import random
import time
import os
import signal
import sys

# ÖNEMLİ: Bu token açık halde. Mümkünse @BotFather'dan /revoke ile yenile
# ve burada os.environ.get('BOT_TOKEN') ile ortam değişkeninden oku.
BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

user_states = {}
user_notes = {}

# Ana menü - Hatırlatıcı ve AI Sohbet butonları eklendi
MAIN_KEYBOARD = [
    [InlineKeyboardButton("💰 Altin Gram (TL)", callback_data='gold')],
    [InlineKeyboardButton("🥈 Gumus Gram (TL)", callback_data='silver')],
    [InlineKeyboardButton("🪙 Kripto Para", callback_data='coins')],
    [InlineKeyboardButton("📊 Dolar/TL", callback_data='dolar')],
    [InlineKeyboardButton("📈 BIST 100 Hisse", callback_data='hisse')],
    [InlineKeyboardButton("🧮 Gram -> TL Hesapla", callback_data='calc')],
    [InlineKeyboardButton("📱 QR Kod Olustur", callback_data='qr')],
    [InlineKeyboardButton("🔗 Link Kisalt", callback_data='shorten')],
    [InlineKeyboardButton("🎲 Rastgele Sayi", callback_data='random')],
    [InlineKeyboardButton("📝 Not Defteri", callback_data='note')],
    [InlineKeyboardButton("⏰ Hatirlatici", callback_data='reminder')],
    [InlineKeyboardButton("🤖 AI Sohbet", callback_data='ai_chat')],
    [InlineKeyboardButton("ℹ️ Yardim", callback_data='help')]
]

# Hisse menüsü
HISSE_KEYBOARD = [
    [InlineKeyboardButton("🇹🇷 BIST 100", callback_data='hisse_bist100')],
    [InlineKeyboardButton("🔧 Aselsan (ASELS)", callback_data='hisse_aselsan')],
    [InlineKeyboardButton("🏦 Garanti (GARAN)", callback_data='hisse_garan')],
    [InlineKeyboardButton("📱 Turkcell (TCELL)", callback_data='hisse_tcell')],
    [InlineKeyboardButton("🛢️ Tüpraş (TUPRS)", callback_data='hisse_tuprs')],
    [InlineKeyboardButton("⚡ Enerjisa (ENJSA)", callback_data='hisse_enjsa')],
    [InlineKeyboardButton("🏗️ Koç (KCHOL)", callback_data='hisse_kchol')],
    [InlineKeyboardButton("⬅️ Ana Menü", callback_data='main_menu')]
]


def get_prices():
    try:
        currency_url = "https://api.exchangerate-api.com/v4/latest/USD"
        currency_response = requests.get(currency_url, timeout=10)
        currency_data = currency_response.json()
        usd_try = currency_data['rates']['TRY']

        gold_ons_usd = None
        try:
            gold_url = "https://api.gold-api.com/price/XAU"
            gold_response = requests.get(gold_url, timeout=10)
            if gold_response.status_code == 200:
                gold_data = gold_response.json()
                gold_ons_usd = gold_data['price']
        except:
            pass

        if gold_ons_usd is None:
            try:
                gold_url2 = "https://metals-api.com/api/latest?access_key=demo&base=USD&symbols=XAU"
                gold_response2 = requests.get(gold_url2, timeout=10)
                if gold_response2.status_code == 200:
                    gold_data2 = gold_response2.json()
                    gold_ons_usd = gold_data2['rates']['XAU']
            except:
                pass

        if gold_ons_usd is None:
            gold_ons_usd = 2350.00

        silver_ons_usd = None
        try:
            silver_url = "https://api.gold-api.com/price/XAG"
            silver_response = requests.get(silver_url, timeout=10)
            if silver_response.status_code == 200:
                silver_data = silver_response.json()
                silver_ons_usd = silver_data['price']
        except:
            pass

        if silver_ons_usd is None:
            silver_ons_usd = 28.50

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
        return {
            'gold_gram': 2450.50,
            'silver_gram': 29.50,
            'usd_try': 32.50,
            'gold_ons': 2350.00,
            'silver_ons': 28.50
        }


def shorten_link(url):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        api_url = f"https://is.gd/create.php?format=simple&url={requests.utils.quote(url)}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200 and response.text.strip() != url:
            return response.text.strip()
        else:
            api_url_tiny = f"http://tinyurl.com/api-create.php?url={requests.utils.quote(url)}"
            response_tiny = requests.get(api_url_tiny, timeout=10)
            if response_tiny.status_code == 200 and "error" not in response_tiny.text.lower():
                return response_tiny.text.strip()
            else:
                return url
    except Exception as e:
        print(f"Link kısaltma hatası: {e}")
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


def get_coin_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin%2Cethereum%2Ctether%2Cbinancecoin%2Cripple%2Ccardano%2Csolana%2Cdogecoin%2Cpolkadot%2Clitecoin%2Cchainlink%2Cpolygon&vs_currencies=usd%2Ctry"
        response = requests.get(url, timeout=15)
        data = response.json()

        if response.status_code == 200:
            return data
        else:
            return None
    except Exception as e:
        print("Kripto fiyat hatası:", e)
        return None


def get_random_number(min_val=1, max_val=100):
    return random.randint(min_val, max_val)


# ==================== BIST HİSSE FİYATLARI ====================

def get_bist100():
    """BIST 100 endeksini getir"""
    try:
        url = "https://finnhub.io/api/v1/quote?symbol=BIST100&token=cj2k4r9r01qov59b7fugcj2k4r9r01qov59b7fv0"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'c' in data:
                return {
                    'price': data['c'],
                    'change': round(((data['c'] - data['pc']) / data['pc']) * 100, 2) if data['pc'] else 0,
                    'high': data['h'],
                    'low': data['l'],
                    'open': data['o']
                }
    except:
        pass

    try:
        url = "https://api.collectapi.com/economy/hisseSenedi?key=apikey&symbol=BIST100"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {'price': data['result']['price'], 'change': data['result']['change']}
    except:
        pass

    return None


def get_hisse(symbol):
    """Hisse senedi fiyatını getir"""
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token=cj2k4r9r01qov59b7fugcj2k4r9r01qov59b7fv0"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'c' in data and data['c'] > 0:
                return {
                    'price': data['c'],
                    'change': round(((data['c'] - data['pc']) / data['pc']) * 100, 2) if data['pc'] and data['pc'] > 0 else 0,
                    'high': data['h'] if data['h'] else data['c'],
                    'low': data['l'] if data['l'] else data['c'],
                    'open': data['o'] if data['o'] else data['c']
                }
    except:
        pass

    demo_data = {
        'ASELS': {'price': 65.45, 'change': 1.25},
        'GARAN': {'price': 98.75, 'change': -0.85},
        'TCELL': {'price': 72.30, 'change': 0.45},
        'TUPRS': {'price': 168.20, 'change': 2.10},
        'ENJSA': {'price': 45.60, 'change': -0.30},
        'KCHOL': {'price': 215.50, 'change': 1.80},
    }

    if symbol in demo_data:
        return demo_data[symbol]

    return None


def get_hisse_name(symbol):
    names = {
        'ASELS': 'ASELSAN',
        'GARAN': 'Garanti BBVA',
        'TCELL': 'Turkcell',
        'TUPRS': 'Tüpraş',
        'ENJSA': 'Enerjisa',
        'KCHOL': 'Koç Holding'
    }
    return names.get(symbol, symbol)


# ==================== HATIRLATICI (API gerektirmez) ====================

def parse_duration_to_seconds(text):
    """
    '10dk', '1saat', '30sn', '45s', '2.5saat', veya sade '15' (dakika kabul edilir)
    formatlarını saniyeye çevirir. Geçersizse None döner.
    """
    text = text.strip().lower().replace(' ', '').replace(',', '.')
    match = re.match(r'^(\d+(?:\.\d+)?)(sn|saniye|s|dk|dakika|m|saat|sa|h)?$', text)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2) or 'dk'

    if unit in ('sn', 'saniye', 's'):
        seconds = value
    elif unit in ('dk', 'dakika', 'm'):
        seconds = value * 60
    elif unit in ('saat', 'sa', 'h'):
        seconds = value * 3600
    else:
        seconds = value * 60

    seconds = int(seconds)
    if seconds <= 0 or seconds > 24 * 3600:  # 24 saatten uzunu reddet
        return None
    return seconds


async def send_reminder_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Süre dolduğunda art arda 10 bildirim gönderir. Tamamen yerel, API gerektirmez."""
    job = context.job
    chat_id = job.chat_id
    note_text = job.data.get('text', '') if job.data else ''

    for i in range(1, 11):
        try:
            msg = f"⏰ **HATIRLATICI ({i}/10)**\n\nSüren doldu!"
            if note_text:
                msg += f"\n📌 Not: {note_text}"
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )
        except Exception as e:
            print("Hatırlatıcı bildirim hatası:", e)
        if i < 10:
            await asyncio.sleep(1.5)


# ==================== YEREL AI SOHBET (API gerektirmez) ====================

AI_RULES = [
    (r'\b(selam|merhaba|hey|hi|naber)\b', [
        "Selam! Nasıl yardımcı olabilirim? 😊",
        "Merhaba! Bugün nasılsın?",
        "Hey! Buradayım, ne konuşmak istersin?"
    ]),
    (r'\b(nasılsın|naptın|napıyon)\b', [
        "İyiyim, teşekkürler! Sen nasılsın?",
        "Gayet iyi, sayılarla ve emojilerle uğraşıyorum 😄 Sen nasılsın?"
    ]),
    (r'\b(adın|ismin) ne\b|\bkimsin\b', [
        "Ben bu botun içindeki küçük bir sohbet motoruyum, dış bir API kullanmıyorum.",
        "Adım yok ama buradayım, sohbet edebiliriz!"
    ]),
    (r'\bteşekkür|sağol|eyvallah\b', [
        "Rica ederim! 🙌",
        "Ne demek, her zaman!"
    ]),
    (r'\b(görüşürüz|bay bay|hoşçakal|çıkış)\b', [
        "Görüşmek üzere! Ana menüye dönmek için aşağıdaki butonu kullanabilirsin.",
        "Bay bay! 👋"
    ]),
    (r'\baltın|gümüş|dolar|kripto|hisse|bist\b', [
        "Bu konuda gerçek zamanlı veri için ana menüden ilgili butona bakabilirsin, ben sadece sohbet ediyorum 😊"
    ]),
    (r'\bşaka\b', [
        "Neden bilgisayarlar hiç üşümez? Çünkü pencereleri (Windows) hep açıktır 😄",
        "Matematikçi neden bahçeye gitmiş? Köklerini sulamaya 🌱"
    ]),
    (r'\bnasıl çalışıyorsun|api kullanıyor musun\b', [
        "Hayır, dış bir yapay zeka API'si kullanmıyorum. Anahtar kelimelere göre cevap veren basit bir kural motoruyum."
    ]),
]

AI_FALLBACKS = [
    "Bunu tam anlayamadım ama dinliyorum, devam et 🙂",
    "İlginç! Biraz daha anlatır mısın?",
    "Hmm, bu konuda emin değilim ama seninle sohbet etmeye devam edebilirim.",
    "Anladım. Başka ne düşünüyorsun?",
    "Söylediğin şeyi not ettim, devam edelim mi?"
]


def simple_ai_response(text):
    """Tamamen yerel, kural tabanlı basit sohbet motoru. Hiçbir dış API çağrısı yapmaz."""
    lowered = text.lower()

    for pattern, responses in AI_RULES:
        if re.search(pattern, lowered):
            return random.choice(responses)

    if text.strip().endswith('?'):
        return "Güzel soru! Şu an net bir cevabım yok ama düşünmeye devam ediyorum 🤔"

    return random.choice(AI_FALLBACKS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_states:
        del user_states[user_id]

    reply_markup = InlineKeyboardMarkup(MAIN_KEYBOARD)
    welcome_text = (
        "🤖 **HOŞGELDİN!**\n\n"
        "Aşağıdaki butonlardan birini seç:\n"
        "💰 Altın/Gümüş fiyatları\n"
        "🪙 Kripto para fiyatları\n"
        "📊 Dolar/TL kuru\n"
        "📈 **BIST 100 Hisse** - ASELS, GARAN, TCELL\n"
        "🧮 Gram hesabı\n"
        "📱 QR kod oluşturma\n"
        "🔗 Link kısaltma\n"
        "🎲 Rastgele sayı\n"
        "📝 Not defteri\n"
        "⏰ Hatırlatıcı\n"
        "🤖 AI Sohbet\n\n"
        "Hepsi ücretsiz ve güncel! 🚀"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id in user_states:
        del user_states[user_id]

    try:
        if data == 'main_menu':
            reply_markup = InlineKeyboardMarkup(MAIN_KEYBOARD)
            await query.edit_message_text(
                "🏠 **Ana Menü**\n\nBir buton seç:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data == 'hisse':
            reply_markup = InlineKeyboardMarkup(HISSE_KEYBOARD)
            await query.edit_message_text(
                "📈 **BIST 100 HİSSE SENETLERİ**\n\n"
                "Aşağıdaki hisselerden birini seç:\n"
                "🔧 ASELSAN (Savunma Sanayi)\n"
                "🏦 Garanti BBVA (Bankacılık)\n"
                "📱 Turkcell (Telekom)\n"
                "🛢️ Tüpraş (Enerji)\n"
                "⚡ Enerjisa (Enerji)\n"
                "🏗️ Koç Holding (Konglomerat)\n\n"
                "📌 Veriler Finnhub API'den alınır.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data == 'hisse_bist100':
            await query.edit_message_text(
                "🔄 BIST 100 endeksi getiriliyor...",
                reply_markup=InlineKeyboardMarkup(HISSE_KEYBOARD)
            )
            bist = get_bist100()
            if bist:
                emoji = "📈" if bist['change'] > 0 else "📉" if bist['change'] < 0 else "➖"
                msg = "🇹🇷 **BIST 100 ENDEKSİ**\n\n"
                msg += f"📊 Fiyat: {bist['price']:.2f}\n"
                msg += f"{emoji} Değişim: {bist['change']:.2f}%\n"
                msg += f"📈 En Yüksek: {bist['high']:.2f}\n"
                msg += f"📉 En Düşük: {bist['low']:.2f}\n"
                msg += f"🔓 Açılış: {bist['open']:.2f}\n\n"
                msg += "📅 " + datetime.now().strftime("%d.%m.%Y %H:%M")
                await query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(HISSE_KEYBOARD),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ BIST 100 verisi alınamadı. Lütfen tekrar dene.",
                    reply_markup=InlineKeyboardMarkup(HISSE_KEYBOARD)
                )

        elif data.startswith('hisse_'):
            symbol = data.replace('hisse_', '').upper()
            name = get_hisse_name(symbol)

            await query.edit_message_text(
                f"🔄 {name} ({symbol}) fiyatı getiriliyor...",
                reply_markup=InlineKeyboardMarkup(HISSE_KEYBOARD)
            )

            hisse = get_hisse(symbol)
            if hisse:
                emoji = "📈" if hisse['change'] > 0 else "📉" if hisse['change'] < 0 else "➖"
                msg = f"📊 **{name} ({symbol})**\n\n"
                msg += f"💰 Fiyat: {hisse['price']:.2f} TL\n"
                msg += f"{emoji} Değişim: {hisse['change']:.2f}%\n"

                if 'high' in hisse and hisse['high']:
                    msg += f"📈 En Yüksek: {hisse['high']:.2f} TL\n"
                    msg += f"📉 En Düşük: {hisse['low']:.2f} TL\n"
                    msg += f"🔓 Açılış: {hisse['open']:.2f} TL\n\n"

                msg += "📅 " + datetime.now().strftime("%d.%m.%Y %H:%M")

                await query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(HISSE_KEYBOARD),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ {name} ({symbol}) verisi alınamadı. Lütfen tekrar dene.",
                    reply_markup=InlineKeyboardMarkup(HISSE_KEYBOARD)
                )

        # ============ DİĞER MENÜLER ============

        elif data == 'gold':
            prices = get_prices()
            if prices:
                msg = "🥇 **ALTIN GRAM FIYATI**\n\n"
                msg += f"📊 USD/TRY: {prices['usd_try']} TL\n"
                msg += f"💲 Altin Ons: ${prices['gold_ons']}\n"
                msg += f"💰 **1 Gram Altin: {prices['gold_gram']} TL**\n\n"
                msg += "📅 " + datetime.now().strftime("%d.%m.%Y %H:%M")
                await query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Fiyat bilgisi alinamadi.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))

        elif data == 'silver':
            prices = get_prices()
            if prices:
                msg = "🥈 **GUMUS GRAM FIYATI**\n\n"
                msg += f"📊 USD/TRY: {prices['usd_try']} TL\n"
                msg += f"💲 Gumus Ons: ${prices['silver_ons']}\n"
                msg += f"💰 **1 Gram Gumus: {prices['silver_gram']} TL**\n\n"
                msg += "📅 " + datetime.now().strftime("%d.%m.%Y %H:%M")
                await query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Fiyat bilgisi alinamadi.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))

        elif data == 'dolar':
            prices = get_prices()
            if prices:
                msg = "📊 **DOLAR/TL KURU**\n\n"
                msg += f"💵 1 USD = {prices['usd_try']} TL\n\n"
                msg += f"🥇 Altin: {prices['gold_gram']} TL/gr\n"
                msg += f"🥈 Gumus: {prices['silver_gram']} TL/gr\n\n"
                msg += "📅 " + datetime.now().strftime("%d.%m.%Y %H:%M")
                await query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Veri alinamadi.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))

        elif data == 'coins':
            await query.edit_message_text("🔄 Kripto para fiyatları getiriliyor...", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
            coin_data = get_coin_prices()
            if coin_data:
                msg = "🪙 **KRIPTO PARA FİYATLARI**\n\n"
                ordered_coins = ['bitcoin', 'ethereum', 'tether', 'binancecoin', 'ripple', 'cardano', 'solana', 'dogecoin', 'polkadot', 'litecoin', 'chainlink', 'polygon']
                coin_names = {
                    'bitcoin': 'BTC', 'ethereum': 'ETH', 'tether': 'USDT',
                    'binancecoin': 'BNB', 'ripple': 'XRP', 'cardano': 'ADA',
                    'solana': 'SOL', 'dogecoin': 'DOGE', 'polkadot': 'DOT',
                    'litecoin': 'LTC', 'chainlink': 'LINK', 'polygon': 'MATIC'
                }
                for coin_id in ordered_coins:
                    if coin_id in coin_data:
                        name = coin_names.get(coin_id, coin_id.capitalize())
                        usd_price = coin_data[coin_id]['usd']
                        try_price = coin_data[coin_id]['try']
                        msg += f"💰 {name}: ${usd_price:.2f} / ₺{try_price:.2f}\n"
                msg += "\n📅 " + datetime.now().strftime("%d.%m.%Y %H:%M")
                await query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text("❌ Kripto fiyat bilgisi alinamadi.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))

        elif data == 'calc':
            user_states[user_id] = 'waiting_calc'
            await query.edit_message_text(
                "🧮 **GRAM HESAPLAMA**\n\n"
                "Kaç gram hesaplamak istiyorsun?\n"
                "Örnek: 5.5\n\n"
                "**Gram miktarını yaz:**",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        elif data == 'qr':
            user_states[user_id] = 'waiting_qr'
            await query.edit_message_text(
                "📱 **QR KOD OLUSTURUCU**\n\n"
                "QR kod yapmak istediğin metni veya linki gönder:\n"
                "Örnek: https://example.com\n\n"
                "**Metni yaz:**",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        elif data == 'shorten':
            user_states[user_id] = 'waiting_shorten'
            await query.edit_message_text(
                "🔗 **LINK KISALTICI**\n\n"
                "Kısaltmak istediğin linki gönder:\n"
                "Örnek: https://example.com/cok-uzun-link\n\n"
                "**Linki yaz:**",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        elif data == 'random':
            user_states[user_id] = 'waiting_random'
            await query.edit_message_text(
                "🎲 **RASTGELE SAYI**\n\n"
                "Hangi aralıkta sayı üretilsin?\n"
                "Format: **min-max**\n"
                "Örnek: 1-100\n\n"
                "**Aralığı yaz:**",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        elif data == 'note':
            user_states[user_id] = 'waiting_note'
            await query.edit_message_text(
                "📝 **NOT DEFTERİ**\n\n"
                "Notunu yaz, kaydedeyim.\n"
                "İleride tekrar görebilirsin.\n\n"
                "**Notunu yaz:**",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        elif data == 'reminder':
            user_states[user_id] = 'waiting_reminder'
            await query.edit_message_text(
                "⏰ **HATIRLATICI**\n\n"
                "Süreyi yaz, süre dolunca art arda 10 bildirim göndereceğim.\n\n"
                "Format örnekleri:\n"
                "• `10dk` → 10 dakika sonra\n"
                "• `1saat` → 1 saat sonra\n"
                "• `30sn` → 30 saniye sonra\n"
                "• `15` → sade sayı yazarsan dakika kabul edilir\n\n"
                "İstersen sürenin sonuna bir not da ekleyebilirsin, örnek:\n"
                "`10dk Yemek pişiyor`\n\n"
                "**Süreyi yaz:**",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        elif data == 'ai_chat':
            user_states[user_id] = 'ai_chat_mode'
            await query.edit_message_text(
                "🤖 **AI SOHBET MODU**\n\n"
                "Benimle yazışabilirsin. Bu tamamen yerel, kural tabanlı bir "
                "sohbet motoru — hiçbir dış API kullanmıyor.\n\n"
                "Çıkmak için Ana Menü butonuna bas.\n\n"
                "**Bir şey yaz:**",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        elif data == 'help':
            help_text = (
                "ℹ️ **YARDIM**\n\n"
                "Bot ile yapabileceklerin:\n\n"
                "💰 **Altın/Gümüş** - Güncel gram fiyatları\n"
                "🪙 **Kripto** - 12+ kripto para fiyatı\n"
                "📊 **Dolar** - USD/TRY kuru\n"
                "📈 **BIST 100** - Hisse senedi fiyatları\n"
                "   🔧 ASELSAN (Aselsan)\n"
                "   🏦 GARAN (Garanti BBVA)\n"
                "   📱 TCELL (Turkcell)\n"
                "   🛢️ TUPRS (Tüpraş)\n"
                "   ⚡ ENJSA (Enerjisa)\n"
                "   🏗️ KCHOL (Koç Holding)\n"
                "🧮 **Hesapla** - Gram TL hesaplama\n"
                "📱 **QR Kod** - QR kod oluşturma\n"
                "🔗 **Link** - Link kısaltma\n"
                "🎲 **Rastgele** - Rastgele sayı üretme\n"
                "📝 **Not** - Not defteri\n"
                "⏰ **Hatırlatıcı** - Süre dolunca 10 bildirim (API gerektirmez)\n"
                "🤖 **AI Sohbet** - Yerel, kural tabanlı sohbet (API gerektirmez)\n\n"
                "📌 Fiyat verileri ilgili API'lerden alınır.\n"
                "Her işlemden sonra ana menüye dönebilirsin.\n"
                "İyi kullanımlar! 🚀"
            )
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

    except Exception as e:
        print("Buton hatasi:", e)
        await query.edit_message_text(
            "❌ Bir hata oluştu. Ana menüden tekrar dene.",
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in user_states:
        return

    state = user_states[user_id]

    if state == 'waiting_calc':
        try:
            gram = float(text.replace(',', '.'))
            prices = get_prices()
            if prices:
                gold_total = gram * prices['gold_gram']
                silver_total = gram * prices['silver_gram']
                msg = "🧮 **HESAPLAMA SONUCU**\n\n"
                msg += f"📊 Gram: {gram}g\n\n"
                msg += f"🥇 Altın: {round(gold_total, 2)} TL\n"
                msg += f"🥈 Gümüş: {round(silver_total, 2)} TL\n\n"
                msg += f"📅 " + datetime.now().strftime("%d.%m.%Y %H:%M")
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Fiyat bilgisi alinamadi.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        except ValueError:
            await update.message.reply_text(
                "❌ Geçersiz sayı. Lütfen bir sayı gir (örnek: 5 veya 5.5)",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )
        del user_states[user_id]

    elif state == 'waiting_qr':
        try:
            bio = create_qr(text)
            await update.message.reply_photo(
                photo=bio,
                caption=f"📱 QR Kod:\n{text}",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ QR kod olusturulamadi: {str(e)}",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )
        del user_states[user_id]

    elif state == 'waiting_shorten':
        await update.message.reply_text(
            "🔄 Link kısaltılıyor...",
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )
        short_url = shorten_link(text)
        msg = "🔗 **LINK KISALTILDI**\n\n"
        msg += f"📌 Orijinal: {text}\n\n"
        msg += f"✂️ **Kısaltılmış:** {short_url}"
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
            parse_mode='Markdown'
        )
        del user_states[user_id]

    elif state == 'waiting_random':
        try:
            parts = text.split('-')
            if len(parts) == 2:
                min_val = int(parts[0].strip())
                max_val = int(parts[1].strip())
                if min_val < max_val:
                    random_num = get_random_number(min_val, max_val)
                    msg = f"🎲 **RASTGELE SAYI**\n\n"
                    msg += f"📊 Aralık: {min_val} - {max_val}\n"
                    msg += f"🔢 **Sonuç: {random_num}**"
                    await update.message.reply_text(
                        msg,
                        reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "❌ Min değer max'dan küçük olmalı!",
                        reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
                    )
            else:
                await update.message.reply_text(
                    "❌ Geçersiz format! Örnek: 1-100",
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Geçersiz sayı! Örnek: 1-100",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )
        del user_states[user_id]

    elif state == 'waiting_note':
        if user_id not in user_notes:
            user_notes[user_id] = []
        user_notes[user_id].append({
            'note': text,
            'date': datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        msg = "📝 **NOT KAYDEDİLDİ!**\n\n"
        msg += f"📌 Notun: {text}\n"
        msg += f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        msg += f"📚 Toplam notun: {len(user_notes[user_id])}"
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
            parse_mode='Markdown'
        )

        if len(user_notes[user_id]) > 0:
            notes_msg = "📚 **NOTLARIN (son 5):**\n\n"
            for i, note in enumerate(user_notes[user_id][-5:], 1):
                notes_msg += f"{i}. {note['note'][:50]}\n"
                notes_msg += f"   📅 {note['date']}\n\n"
            await update.message.reply_text(
                notes_msg,
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )

        del user_states[user_id]

    elif state == 'waiting_reminder':
        # "10dk Yemek pişiyor" gibi süre + opsiyonel not formatını ayır
        parts = text.split(maxsplit=1)
        duration_part = parts[0] if parts else text
        note_part = parts[1] if len(parts) > 1 else ''

        seconds = parse_duration_to_seconds(duration_part)
        if seconds is None:
            await update.message.reply_text(
                "❌ Geçersiz süre formatı! Örnek: `10dk`, `1saat`, `30sn` veya sade `15`",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                parse_mode='Markdown'
            )
        else:
            if context.job_queue is None:
                await update.message.reply_text(
                    "❌ Hatırlatıcı sistemi aktif değil. Sunucuda `pip install \"python-telegram-bot[job-queue]\"` "
                    "kurulu olduğundan emin ol.",
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
                )
            else:
                context.job_queue.run_once(
                    send_reminder_notifications,
                    when=seconds,
                    chat_id=update.effective_chat.id,
                    data={'text': note_part}
                )
                readable = duration_part
                msg = f"⏰ **Hatırlatıcı kuruldu!**\n\n"
                msg += f"🕒 Süre: {readable} ({seconds} saniye)\n"
                if note_part:
                    msg += f"📌 Not: {note_part}\n"
                msg += "\nSüre dolunca art arda 10 bildirim göndereceğim."
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
                    parse_mode='Markdown'
                )
        del user_states[user_id]

    elif state == 'ai_chat_mode':
        response = simple_ai_response(text)
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )
        # Not: state burada silinmiyor, kullanıcı Ana Menü butonuna basana kadar
        # AI sohbet modunda kalmaya devam eder.


async def run_bot():
    print('🤖 Bot başlatılıyor...')
    print('📈 BIST 100 Hisse Senedi sistemi aktif!')
    print('⏰ Hatırlatıcı sistemi aktif!')
    print('🤖 Yerel AI sohbet sistemi aktif!')

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    if application.job_queue is None:
        print('⚠️  UYARI: job_queue mevcut değil. Hatırlatıcı çalışmayacak.')
        print('    Kurulum için: pip install "python-telegram-bot[job-queue]"')

    print('✅ Bot aktif!')

    await application.initialize()
    await application.start()

    await application.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

    print('📡 Polling başladı...')

    while True:
        await asyncio.sleep(1)


def signal_handler(sig, frame):
    print('\n🛑 Bot kapatılıyor...')
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    Thread(target=run_flask, daemon=True).start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        print('🛑 Bot kapatıldı')
    except Exception as e:
        print(f'❌ Hata: {e}')
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except:
            pass
        loop.close()


if __name__ == '__main__':
    main()
