import asyncio
import requests
import qrcode
import io
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'
GROQ_API_KEY = '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'
GOLD_API_KEY = 'goldapi-615dd989f010af41bbde17b0213d7075-io'
AI_MODEL = 'llama3-8b-8192'

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

user_states = {}
user_chat_history = {}

# Ana menüye 'coins' butonu eklendi
MAIN_KEYBOARD = [
    [InlineKeyboardButton("Altin Gram (TL)", callback_data='gold')],
    [InlineKeyboardButton("Gumus Gram (TL)", callback_data='silver')],
    [InlineKeyboardButton("Kripto Para (Coin)", callback_data='coins')], # Yeni buton
    [InlineKeyboardButton("Hesapla (Gram -> TL)", callback_data='calc')],
    [InlineKeyboardButton("QR Kod Olustur", callback_data='qr')],
    [InlineKeyboardButton("Link Kisalt", callback_data='shorten')],
    [InlineKeyboardButton("AI Sohbet (Groq)", callback_data='ai_chat')]
]

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

# Link kısaltıcı fonksiyonu düzeltildi
def shorten_link(url):
    try:
        # URL'nin geçerli bir format olduğunu kontrol et
        if not url.startswith(('http://', 'https://')):
             url = 'http://' + url
        # is.gd API'si kullanılıyor
        api_url = f"https://is.gd/create.php?format=simple&url={requests.utils.quote(url)}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200 and response.text.strip() != url: # Hata durumunda orijinal döner
            return response.text.strip()
        else:
            # Eğer is.gd başarısız olursa, tinyurl'ı alternatif olarak dene
            api_url_tiny = f"http://tinyurl.com/api-create.php?url={requests.utils.quote(url)}"
            response_tiny = requests.get(api_url_tiny, timeout=10)
            if response_tiny.status_code == 200 and "error" not in response_tiny.text.lower():
                 return response_tiny.text.strip()
            else:
                return url # Her iki servis de başarısız olursa orijinal linki döndür
    except Exception as e:
        print(f"Link kısaltma hatası: {e}")
        return url # Hata durumunda orijinal linki döndür


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
            "Authorization": "Bearer " + GROQ_API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "model": AI_MODEL,
            "messages": user_chat_history[user_id]
        }

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
        else:
            return "AI yanit veremedi. Hata: " + str(response.status_code)
    except Exception as e:
        return "AI hatasi: " + str(e)

# Yeni: Kripto para fiyatları için fonksiyon
def get_coin_prices():
    try:
        # CoinGecko API'sinden fiyat bilgilerini al
        # coins = ['bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano', 'solana', 'dogecoin', 'polkadot', 'litecoin', 'chainlink']
        # coins_str = ','.join(coins)
        # url = f"https://api.coingecko.com/api/v3/simple/price?ids={coins_str}&vs_currencies=usd%2Ctry"
        # Daha hızlı örnek veri için sınırlı coin listesi
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_states:
        del user_states[user_id]

    reply_markup = InlineKeyboardMarkup(MAIN_KEYBOARD)
    await update.message.reply_text(
        'Altin & Gumus Bot + AI + Coin\n\nBir buton sec:',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ÖNEMLİ: Butona basıldığında eski state'i temizle
    if user_id in user_states:
        del user_states[user_id]

    try:
        if data == 'gold':
            prices = get_prices()
            if prices:
                msg = "ALTI GRAM FIYATI (GÜNCEL)\n\n"
                msg += "USD/TRY: " + str(prices['usd_try']) + " TL\n"
                msg += "Altin Ons: $" + str(prices['gold_ons']) + "\n"
                msg += "1 Gram Altin: " + str(prices['gold_gram']) + " TL\n\n"
                msg += "Kaynak: GoldAPI.io"
                await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
            else:
                await query.edit_message_text("Fiyat bilgisi alinamadi. GoldAPI key kontrol et.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))

        elif data == 'silver':
            prices = get_prices()
            if prices:
                msg = "GUMUS GRAM FIYATI (GÜNCEL)\n\n"
                msg += "USD/TRY: " + str(prices['usd_try']) + " TL\n"
                msg += "Gumus Ons: $" + str(prices['silver_ons']) + "\n"
                msg += "1 Gram Gumus: " + str(prices['silver_gram']) + " TL\n\n"
                msg += "Kaynak: GoldAPI.io"
                await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
            else:
                await query.edit_message_text("Fiyat bilgisi alinamadi. GoldAPI key kontrol et.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))

        # Yeni: Coin butonu işleyicisi
        elif data == 'coins':
            await query.edit_message_text("Kripto para fiyatları getiriliyor...", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
            coin_data = get_coin_prices()
            if coin_data:
                msg = "KRIPTO PARA FİYATLARI (GÜNCEL)\n\n"
                # Coinleri sıralı bir şekilde gösterelim
                ordered_coins = ['bitcoin', 'ethereum', 'tether', 'binancecoin', 'ripple', 'cardano', 'solana', 'dogecoin', 'polkadot', 'litecoin', 'chainlink', 'polygon']
                for coin_id in ordered_coins:
                    if coin_id in coin_data:
                        coin_name = coin_id.capitalize() # Basit isim
                        usd_price = coin_data[coin_id]['usd']
                        try_price = coin_data[coin_id]['try']
                        msg += f"{coin_name}: ${usd_price:.2f} / ₺{try_price:.2f}\n"
                msg += "\nKaynak: CoinGecko"
                await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
            else:
                await query.edit_message_text("Kripto fiyat bilgisi alinamadi.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))


        elif data == 'calc':
            user_states[user_id] = 'waiting_calc'
            await query.edit_message_text(
                "HESAPLAMA MODU\n\n"
                "Kac gram hesaplamak istiyorsun?\n"
                "Ornek: 5\n\n"
                "Gram miktarini yaz:",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )

        elif data == 'qr':
            user_states[user_id] = 'waiting_qr'
            await query.edit_message_text(
                "QR KOD OLUSTURUCU\n\n"
                "QR kod yapmak istedigin linki gonder:\n"
                "Ornek: https://example.com",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )

        elif data == 'shorten':
            user_states[user_id] = 'waiting_shorten'
            await query.edit_message_text(
                "LINK KISALTICI\n\n"
                "Kisaltmak istedigin linki gonder:\n"
                "Ornek: https://example.com/cok-uzun-link",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )

        elif data == 'ai_chat':
            user_states[user_id] = 'waiting_ai'
            await query.edit_message_text(
                "AI SOHBET (Groq Llama3)\n\n"
                "Artik AI ile sohbet edebilirsin!\n"
                "Sorularini yaz, cevap verecek.\n\n"
                "Ana menuye donmek icin bir butona tikla.",
                reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD)
            )
    except Exception as e:
        print("Buton hatasi:", e)

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
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
            else:
                await update.message.reply_text("Fiyat bilgisi alinamadi.", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        except ValueError:
            await update.message.reply_text("Gecersiz sayi. Lutfen bir sayi gir (orn: 5)", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        del user_states[user_id]

    elif state == 'waiting_qr':
        try:
            bio = create_qr(text)
            await update.message.reply_photo(photo=bio, caption="QR Kod:\n" + text, reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        except Exception as e:
            await update.message.reply_text("QR kod olusturulamadi: " + str(e), reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        del user_states[user_id]

    elif state == 'waiting_shorten':
        # Link kısaltma işlemi burada yapılacak
        await update.message.reply_text("Link kisaltiliyor...", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        short_url = shorten_link(text)
        msg = "LINK KISALTILDI\n\n"
        msg += "Orijinal: " + text + "\n"
        msg += "Kisa: " + short_url
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        del user_states[user_id] # State'i temizle


    elif state == 'waiting_ai':
        await update.message.reply_text("AI dusunuyor...", reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))
        response = ask_ai(user_id, text)

        if len(response) > 4000:
            response = response[:4000] + "\n\n[Devami kesildi...]"

        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup(MAIN_KEYBOARD))

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
