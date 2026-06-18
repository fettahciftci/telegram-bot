from telegram.ext import Updater, CommandHandler
from flask import Flask
from threading import Thread

BOT_TOKEN = '8904642273:AAF6sQtbS9ZpoSRLNOeZLO9VFTWq1EsAY9s'

app = Flask('')

@app.route('/')
def home():
    return "Bot calisiyor!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start(update, context):
    update.message.reply_text(
        '💰 Altın & Gümüş Bot\n\n'
        '/altin - Altın fiyatı\n'
        '/gumus - Gümüş fiyatı'
    )

def gold(update, context):
    update.message.reply_text('🥇 Altın: $2,345/oz')

def silver(update, context):
    update.message.reply_text('🥈 Gümüş: $28.50/oz')

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("altin", gold))
    dp.add_handler(CommandHandler("gumus", silver))
    
    print('Bot aktif!')
    updater.start_polling()

if __name__ == '__main__':
    Thread(target=run_flask).start()
    main()