import telebot
import mysql.connector
from mysql.connector import errorcode
from app_bot import config

try:
    db = mysql.connector.connect(host=config.DB_HOST,database=config.DB_DATABASE,user=config.DB_USER,
    password=config.DB_PASSWORD)

    bot = telebot.TeleBot(config.BOT_TOKEN)
    from app_bot import botOdessa  # import bot if db connection is successful
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)
else:
    db.close()
