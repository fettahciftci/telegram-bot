from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('💰 Bot hazır!\n/altin - Altın\n/gumus - Gümüş')

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🥇 Altın: $2,345/oz')

async def silver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🥈 Gümüş: $28.50/oz')

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("altin", gold))
    application.add_handler(CommandHandler("gumus", silver))
    print('✅ Bot aktif!')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    Thread(target=run_flask, daemon=True).start()
    main()
