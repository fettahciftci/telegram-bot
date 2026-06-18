from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread
import asyncio

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'

# Flask sunucusu
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Telegram komutları
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('💰 Bot hazır!\n/altin - Altın\n/gumus - Gümüş')

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🥇 Altın: $2,345/oz')

async def silver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🥈 Gümüş: $28.50/oz')

async def run_bot():
    """Bot'u asyncio ile çalıştır"""
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("altin", gold))
    application.add_handler(CommandHandler("gumus", silver))
    
    print('✅ Bot aktif!')
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Sonsuz döngü
    while True:
        await asyncio.sleep(1)

def main():
    # Python 3.14 için manuel event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Flask'ı ayrı thread'de başlat
    Thread(target=run_flask, daemon=True).start()
    
    # Bot'u ana thread'de çalıştır
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        print('Bot kapatıldı')
    finally:
        loop.close()

if __name__ == '__main__':
    main()
