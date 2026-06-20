import asyncio
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

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'
GROQ_API_KEY = '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'

# Daha stabil ve çalışan modeller
# Mixtral daha iyi çalışıyor, llama3 bazen hata veriyor
AI_MODEL = 'mixtral-8x7b-32768'  # veya 'llama3-70b-8192' veya 'gemma2-9b-it'

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

user_states = {}
user_chat_history = {}

# Ana menü
MAIN_KEYBOARD = [
    [InlineKeyboardButton("💰 Altin Gram (TL)", callback_data='gold')],
    [InlineKeyboardButton("🥈 Gumus Gram (TL)", callback_data='silver')],
    [InlineKeyboardButton("🪙 Kripto Para", callback_data='coins')],
    [InlineKeyboardButton("📊 Dolar/TL", callback_data='dolar')],
    [InlineKeyboardButton("🧮 Gram -> TL Hesapla", callback_data='calc')],
    [InlineKeyboardButton("📱 QR Kod Olustur", callback_data='qr')],
    [InlineKeyboardButton("🔗 Link Kisalt", callback_data='shorten')],
    [InlineKeyboardButton("🤖 AI Sohbet", callback_data='ai_chat')],
    [InlineKeyboardButton("🎲 Rastgele Sayi", callback_data='random')],
    [InlineKeyboardButton("📝 Not Defteri", callback_data='note')],
    [InlineKeyboardButton("ℹ️ Yardim", callback_data='help')]
]

def get_prices():
    try:
        currency_url = "https://api.exchangerate-api.com/v4/latest/USD"
        currency_response = requests.get(currency_url, timeout=10)
        currency_data = currency_response.json()
        usd_try = currency_data['rates']['TRY']
        
        # Altın fiyatı için birden fazla API dene
        gold_ons_usd = None
        try:
            # 1. Gold-API (bedava)
            gold_url = "https://api.gold-api.com/price/XAU"
            gold_response = requests.get(gold_url, timeout=10)
            if gold_response.status_code == 200:
                gold_data = gold_response.json()
                gold_ons_usd = gold_data['price']
        except:
            pass
        
        if gold_ons_usd is None:
            try:
                # 2. Metals-API (demo)
                gold_url2 = "https://metals-api.com/api/latest?access_key=demo&base=USD&symbols=XAU"
                gold_response2 = requests.get(gold_url2, timeout=10)
                if gold_response2.status_code == 200:
                    gold_data2 = gold_response2.json()
                    gold_ons_usd = gold_data2['rates']['XAU']
            except:
                pass
        
        if gold_ons_usd is None:
            # 3. Sabit yaklaşık değer (güncel)
            gold_ons_usd = 2350.00
        
        # Gümüş fiyatı
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

# YENİ VE GELİŞMİŞ AI FONKSİYONU - Hata yönetimi ile
def ask_ai(user_id, message):
    try:
        if user_id not in user_chat_history:
            user_chat_history[user_id] = []
        
        user_chat_history[user_id].append({"role": "user", "content": message})
        
        if len(user_chat_history[user_id]) > 10:
            user_chat_history[user_id] = user_chat_history[user_id][-10:]
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": AI_MODEL,
            "messages": user_chat_history[user_id],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        # 3 kez dene (retry mekanizması)
        for attempt in range(3):
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_message = result['choices'][0]['message']['content']
                    user_chat_history[user_id].append({"role": "assistant", "content": ai_message})
                    return ai_message
                elif response.status_code == 401:
                    return "❌ API Key geçersiz! Lütfen Groq API key'ini kontrol et."
                elif response.status_code == 429:
                    if attempt < 2:
                        time.sleep(2)  # Rate limit için bekle
                        continue
                    return "❌ Çok fazla istek gönderildi. Lütfen biraz bekle."
                else:
                    if attempt < 2:
                        time.sleep(1)
                        continue
                    return f"❌ AI hatası: {response.status_code} - {response.text[:100]}"
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(1)
                    continue
                return "❌ Zaman aşımı. Lütfen tekrar dene."
            except Exception as e:
                if attempt < 2:
                    time.sleep(1)
                    continue
                return f"❌ Bağlantı hatası: {str(e)[:100]}"
        
        return "❌ Üzgünüm, AI şu anda cevap veremiyor. Lütfen biraz sonra tekrar dene."
        
    except Exception as e:
        return f"❌ Beklenmeyen hata: {str(e)[:100]}"

def get_coin_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin%2Cethereum%2Ctether%2Cbinancecoin%2Cripple%2Ccardano%2Csolana%2Cdogecoin%2Cpolkadot%2Clitecoin%2Cchainlink%2Cpolygon&vs_currencies=usd%2Ctry"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if response.status_code == 200:
            return data
        else:
            print("CoinGecko API hatası:", response.status_code)
            return None
    except Exception as e:
        print("Kripto fiyat hatası:", e)
        return None

def get_random_number(min_val=1, max_val=100):
    return random.randint(min_val, max_val)

user_notes = {}

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
        "🧮 Gram hesabı\n"
        "📱 QR kod oluşturma\n"
        "🔗 Link kısaltma\n"
        "🤖 AI sohbet (Mixtral)\n"
        "🎲 Rastgele sayı\n"
        "📝 Not defteri\n\n"
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
        if data == 'gold':
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
        
        elif data == 'ai_chat':
            user_states[user_id] = 'waiting_ai'
            await query.edit_message_text(
                "🤖 **AI SOHBET (Mixtral-8x7B)**\n\n"
                "Artık AI ile sohbet edebilirsin!\n"
                "Sorularını yaz, cevap verecek.\n\n"
                "🔄 3 kez deneme yapar, hata durumunda tekrar dener.\n"
                "📌 Not: Ana menüye dönmek için bir butona tıkla.",
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
        
        elif data == 'help':
            help_text = (
                "ℹ️ **YARDIM**\n\n"
                "Bot ile yapabileceklerin:\n\n"
                "💰 **Altın/Gümüş** - Güncel gram fiyatları\n"
                "🪙 **Kripto** - 12+ kripto para fiyatı\n"
                "📊 **Dolar** - USD/TRY kuru\n"
                "🧮 **Hesapla** - Gram TL hesaplama\n"
                "📱 **QR Kod** - QR kod oluşturma\n"
                "🔗 **Link** - Link kısaltma\n"
                "🤖 **AI** - Mixtral-8x7B sohbet\n"
                "🎲 **Rastgele** - Rastgele sayı üretme\n"
                "📝 **Not** - Not defteri\n\n"
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
    
    elif state == 'waiting_ai':
        # AI'ya mesaj göndermeden önce bilgi ver
        wait_msg = await update.message.reply_text(
            "🤖 AI düşünüyor... (en fazla 30 saniye)",
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
        )
        
        response = ask_ai(user_id, text)
        
        if len(response) > 4000:
            response = response[:4000] + "\n\n[Devamı kesildi...]"
        
        # Wait message'ı sil
        await wait_msg.delete()
        
        await update.message.reply_text(
            f"🤖 **AI Cevabı:**\n\n{response}",
            reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD),
            parse_mode='Markdown'
        )
    
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

async def run_bot():
    print('🤖 Bot başlatılıyor...')
    print(f'📌 AI Model: {AI_MODEL}')
    print(f'🔑 API Key: {GROQ_API_KEY[:10]}...')
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print('✅ Bot aktif!')
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
        print('🛑 Bot kapatıldı')
    finally:
        loop.close()

if __name__ == '__main__':
    main()
    
