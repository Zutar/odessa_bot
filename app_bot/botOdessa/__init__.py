from apscheduler.schedulers.background import BackgroundScheduler
from app_bot.botOdessa import functions
from app_bot import db, bot
import telebot

cursor = db.cursor()
user = None

# Start work
@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id

    cursor.execute('SELECT * FROM users WHERE chatId={0}'.format(chat_id))
    data = cursor.fetchone()

    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    if(data is not None):
        keyboard.row('Профиль', 'Новости', 'Заявки', "Погода")
        bot.send_message(message.chat.id, 'Добро пожаловать!\n Я бот который поможет Вам узнать '
        'актуальные новости в Одессе а так же подать заявку на найденную проблему в городе.'
        ' Другие люди могут просматривать поданные заявки и принимать участвие в их решении а '
        'так же в проверке выполнения!', reply_markup=keyboard)
    else:
        keyboard = telebot.types.ReplyKeyboardRemove()
        bot.send_message(chat_id, 'Для начала работы с ботом Вам необходимо пройти простую регистрацию. Как вас зовут?', reply_markup=keyboard)
        bot.register_next_step_handler(message, doReg)

# Get help information
@bot.message_handler(commands=['help'])
def get_help(message):
    text = '*Немного про меня:* \n' \
           '- логин бота @getInfoOdessaBot \n' \
           '- написан на Python \n\n' \
           '*Что я умею:* \n' \
           '- расскажу про последние новости в Одессе \n' \
           '- нашли проблему в городе? Я помогу заполнить вам заявку и она обязательно решится! \n' \
           '- хотите помочь городу? У меня как раз есть невыполненные заявки, я вам покажу! \n\n' \
           '*Как со мной работать? Легко!)* \n' \
           '- для начала напишите /start и пройдите простую регистрацию \n' \
           '- хотите узнать последние новости Одессы? Напишите мне "Новости" или /news \n' \
           '- для создания новой заявки напишите "Новая заявка" или /newTask \n' \
           '- интересно какие до этого заявки создали люди? Напишите "Все заявки" или /allTasks \n'
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Alternative for "Новости"
@bot.message_handler(commands=['news'])
def get_news(message):
    if checkUser(message): functions.showNewsMenu(message)

# Alternative for "Список заявок"
@bot.message_handler(commands=['allTasks'])
def get_news(message):
    if checkUser(message): functions.showtaskList(message, "active", 0)

# Alternative for "Добавить заявку"
@bot.message_handler(commands=['newTask'])
def get_news(message):
    if checkUser(message): functions.createTask(message)

# Handler for main services
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if checkUser(message):
        bot.delete_message(message.chat.id, message.message_id)

        if message.text == "Привет":
            bot.send_message(message.from_user.id, "Привет, чем я могу тебе помочь?")
        elif message.text == "Профиль":
            functions.showProfileMenu(message, user)
        elif message.text == "Новости":
            functions.showNewsMenu(message)
        elif message.text == "Заявки":
            functions.showTasksMenu(message)
        elif message.text == "Главная":
            functions.showMain(message)
        elif message.text == "Предложить новость":
            functions.suggestNews(message)
        elif message.text == "Список заявок":
            functions.showtaskList(message, "active", 0)
        elif message.text == "Добавить заявку":
            functions.createTask(message)
        elif message.text == "Список новостей":
            functions.showNews(message, 0)
        elif message.text == "Погода":
            functions.getWeather(message)
        else:
            bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши /help.")

# Handler for forward or backward news
@bot.callback_query_handler(func=lambda c: c.data.find("news") != -1)
def process_callback(data):
    message = data.message
    args = data.data
    args = args.split(":")
    offset = int(args[1])
    if message is not None: bot.delete_message(message.chat.id, message.message_id)
    functions.showNews(data.message, offset)

# Handler for forward or backward tasks
@bot.callback_query_handler(func=lambda c: c.data.find("tasks") != -1)
def process_callback(data):
    message = data.message
    args = data.data
    args = args.split(":")
    type = args[1]
    offset = int(args[2])
    if message is not None: bot.delete_message(message.chat.id, message.message_id)
    functions.showtaskList(data.message, type, offset)

# Handler for admin commands
@bot.callback_query_handler(func=lambda c: c.data.find("admin") != -1)
def process_callback(data):
    message = data.message
    args = data.data
    args = args.split(":")
    type = args[1]

    if type == 'n':
        data = args[2]
        id = args[3]
        if data == 'del':
            query = 'DELETE FROM news WHERE id=%s' % id
        elif data == 'accept':
            query = 'UPDATE news SET status="checked" WHERE id=%s' % id
        cursor.execute(query)
        db.commit()
    elif type == 'task':
        data = args[2]
        id = args[3]
        if data == 'del':
            query = 'DELETE FROM tasks WHERE id=%s' % id
        elif data == 'accept':
            query = 'UPDATE tasks SET status="active" WHERE id=%s' % id
        cursor.execute(query)
        db.commit()

    bot.delete_message(message.chat.id, message.message_id)



# Register new user and add data to DB
def doReg(message):
    name = message.text
    chat_id = message.chat.id
    cursor.execute('INSERT INTO users VALUE(NULL, "{0}", "{1}", NULL, "");'.format(chat_id, name))
    db.commit()

    info = 'Регистрация прошла успешно!'
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('Профиль', 'Новости', 'Заявки', 'Погода')
    bot.send_message(message.chat.id, info, reply_markup=keyboard)

# Check user data
def checkUser(message):
    global user
    if user is None or user[0] != message.chat.id:
        cursor.execute('SELECT * FROM users WHERE chatId={0}'.format(message.chat.id))
        user = cursor.fetchone()
        if user is not None:
            return True
        else:
            bot.send_message(message.chat.id, "Напишите /start и пройдите регистрацию!")
            return False
    else:
        bot.send_message(message.chat.id, "Напишите /start и пройдите регистрацию!")
        return False


# Parse new information (news) from https://www.ukr.net (see getNews function in functions.py)
scheduler = BackgroundScheduler()
scheduler.add_job(functions.parseNews, 'interval', minutes=30)
scheduler.add_job(functions.parseExchangeRates, 'interval', minutes=1)
scheduler.start()

bot.polling(none_stop=True, interval=0) #infinity_polling
