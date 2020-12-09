import app_bot
from app_bot import db, bot
import telebot
import json, urllib.request
import re
from datetime import datetime
from app_bot import config

cursor = db.cursor()

# Show profile menu
def showProfileMenu(message, user):
    age = user[3]
    if age is None: age="Неизвестно"

    cursor.execute('SELECT COUNT(id) FROM news WHERE status!="new" AND authorId=%s' % message.chat.id)
    newsCount = cursor.fetchone()
    if newsCount is not  None:
        newsCount = newsCount[0]
    else:
        newsCount = 0

    cursor.execute('SELECT COUNT(id) FROM tasks WHERE status!="new" AND authorId=%s' % message.chat.id)
    taskCount = cursor.fetchone()
    if taskCount is not  None:
        taskCount = taskCount[0]
    else:
        taskCount = 0

    info = '*Ваш профиль* \n ID: {0} \n Имя: {1} \n Возраст: {2} \n Количество новостей: {3} \n Количество заявок: {4}'.format(user[0], user[2], age, newsCount, taskCount)
    #keyboard = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, info, parse_mode="Markdown")

# Show news menu
def showNewsMenu(message):

    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('Главная', 'Список новостей', "Предложить новость")
    bot.send_message(message.chat.id, "Новости", reply_markup=keyboard, parse_mode="Markdown")

# Show task window
def showTasksMenu(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('Главная', 'Список заявок', "Добавить заявку")

    bot.send_message(message.chat.id, "Заявки", reply_markup=keyboard, parse_mode="Markdown")

# Show main window
def showMain(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('Профиль', 'Новости', 'Заявки', 'Погода')

    cursor.execute('SELECT * FROM exchange_rates;')
    exchange = cursor.fetchall()
    rates = ""

    for item in exchange:

        rates += "%s/%s            %s / %s\n" % (item[0], item[1], item[2], item[3])

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    info = '*Одесса*\n\n' \
           '*Время:* %s\n\n' \
           '*Курс валют:   Купить/Продать*\n' \
           '' \
           '%s' % (now, rates)

    bot.send_message(message.chat.id, info, reply_markup=keyboard, parse_mode="Markdown")

#
def showNews(message, start):
    markup = telebot.types.InlineKeyboardMarkup()
    news = getNews(1, start)

    if len(news) > 0:
        news = news[0]
        max = news[-1] # get max page
        back = "news:%s" % (start - 1)
        forward = "news:%s" % (start + 1)

        info = '*Последние новости Одессы:* \n'

        date = datetime.utcfromtimestamp(int(news[3])).strftime('%Y-%m-%d %H:%M:%S')
        link = news[4]
        if link != "-":
            link = "Ссылка: %s" % link
        else:
            link = ""

        info += "\n\n" \
                "*%s*\n\n" \
                "%s\n\n" \
                "Дата: *%s*\n" \
                "Автор: *%s*\n\n" \
                "%s" % (news[1], news[2], date, news[6], link)
        if start > -1 and start < 1:
            markup.row(telebot.types.InlineKeyboardButton(text='Вперед', callback_data=forward))
        elif start == int(max) - 1:
            markup.row(telebot.types.InlineKeyboardButton(text='Назад', callback_data=back))
        else:
            markup.row(telebot.types.InlineKeyboardButton(text='Назад', callback_data=back),
            telebot.types.InlineKeyboardButton(text='Вперед', callback_data=forward))


        bot.send_message(message.chat.id, info, reply_markup=markup, parse_mode="Markdown")
    else:
        info = '*На данный момент нет новостей в системе!*'
        bot.send_message(message.chat.id, info, reply_markup=markup, parse_mode="Markdown")

# Get news for user
def getNews(limit, start):
    cursor.execute('SELECT *, COUNT(id) OVER() FROM news WHERE status="checked" ORDER BY ID DESC LIMIT %s OFFSET %s' % (limit, start))
    output = cursor.fetchall()
    return output

# Create news
def suggestNews(message):
    info = "Есть интересная новость? Поделитесь с нами! Напишите заголовок для новости:"
    keyboard = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, info, reply_markup=keyboard)
    bot.register_next_step_handler(message, doNewsS1)

# News step 1
def doNewsS1(message):
    text = message.text
    info = "Теперь напишите основной текст новости:"
    bot.send_message(message.chat.id, info)
    bot.register_next_step_handler(message, doNewsS2, text)

# News step 2
def doNewsS2(message, title):
    text = message.text
    info = "Хотите указать себя как автора новости? (Да/Нет)"
    bot.send_message(message.chat.id, info)
    bot.register_next_step_handler(message, doNewsS3, title, text)

# News step 3
def doNewsS3(message, title, description):
    author = message.text.lower()
    if author == "да":
        author = "@%s" % message.from_user.username
    else:
        author = "Аноним"

    title = re.sub('\'', '\\\'', title)
    description = re.sub('\'', '\\\'', description)

    query = "INSERT INTO news VALUE(NULL, '%s', '%s', '%s', '%s', '%s', '%s', 'new', '%s');" % (
    title, description, int(datetime.now().timestamp()), "-", "-", author, message.chat.id)
    cursor.execute(query)
    db.commit()

    id = cursor.lastrowid

    info = "Новость успешно добавлена и отправлена на модерацию!"
    cursor.execute('SELECT chatId FROM users WHERE type="admin"')
    data = cursor.fetchone()

    # Send message to admin about news
    adminInfo = "*Пользователь предложил новость*\n\n" \
           "*%s*\n" \
           "%s\n" % (title, description)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton(text='Удалить', callback_data="admin:n:del:%s" % id),
               telebot.types.InlineKeyboardButton(text='Добавить', callback_data="admin:n:accept:%s" % id))
    bot.send_message(data[0], adminInfo, reply_markup=markup, parse_mode="Markdown")

    # Send message to user
    bot.send_message(message.chat.id, info)
    showMain(message)

# Parse news from https://www.ukr.net
def parseNews():
    data = urllib.request.urlopen("https://www.ukr.net/news/dat/odessa/1/").read()
    output = json.loads(data)["tops"]
    output.reverse()
    for item in output:
        title = re.sub('\'', '\\\'', item["Title"])
        description = re.sub('\'', '\\\'', item["Description"])
        p_title = re.sub('\'', '\\\'', item["PartnerTitle"])
        query = "INSERT INTO news VALUE(NULL, '%s', '%s', '%s', '%s', '%s', '%s', 'checked', '-');" % (title, description, item["DateCreated"], item["Url"], "-", p_title)
        cursor.execute(query)

    db.commit()

    cursor.execute('SELECT chatId FROM users WHERE type="admin";')
    data = cursor.fetchone()

    info = 'Парсинг новостей завершен!'
    bot.send_message(data[0], info)

# Parse exchange rates
def parseExchangeRates():
    data = urllib.request.urlopen("https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5").read()
    data = json.loads(data)
    cursor.execute('UPDATE exchange_rates SET buy=%s, sale=%s WHERE ccy="USD";' % (data[0]["buy"], data[0]["sale"]))
    cursor.execute('UPDATE exchange_rates SET buy=%s, sale=%s WHERE ccy="EUR";' % (data[1]["buy"], data[1]["sale"]))
    cursor.execute('UPDATE exchange_rates SET buy=%s, sale=%s WHERE ccy="RUR";' % (data[2]["buy"], data[2]["sale"]))
    cursor.execute('UPDATE exchange_rates SET buy=%s, sale=%s WHERE ccy="BTC";' % (data[3]["buy"], data[3]["sale"]))
    db.commit()

# Show task list from DB
def showtaskList(message, type, start):
    cursor.execute('SELECT * FROM tasks;')
    data = cursor.fetchall()

    query = None

    if len(data) > 0:
        markup = telebot.types.InlineKeyboardMarkup()
        back = "tasks:%s:%s" % (type, start - 1)
        forward = "tasks:%s:%s" % (type, start + 1)

        if type=="active":
            info = '*Активные заявки:*'
            query = 'SELECT *, COUNT(id) OVER() FROM tasks WHERE status="active" ORDER BY ID DESC LIMIT 1 OFFSET %s;' % start
        elif type=="finish":
            info = '*Заявки которые ожидают проверки выполнения:*'
            query = 'SELECT *, COUNT(id) OVER() FROM tasks WHERE status="finish" ORDER BY ID DESC LIMIT 1 OFFSET %s;' % start
    else:
        info = '*На данный момент нет заявок в системе. Но вы можете стать первым!*'
        markup = telebot.types.ReplyKeyboardMarkup(True)
        markup.row('Главная', 'Список заявок', "Добавить заявку")

    if query is not None:
        cursor.execute(query)
        data = cursor.fetchone()

        if data is not None:
            max = data[9] # get max page

            if type == "active":
                if start > -1 and start < 1:

                    markup.row(telebot.types.InlineKeyboardButton(text='Вперед', callback_data=forward))
                elif start == int(max) - 1:
                    markup.row(telebot.types.InlineKeyboardButton(text='Назад', callback_data=back))
                else:
                    markup.row(telebot.types.InlineKeyboardButton(text='Назад', callback_data=back),
                               telebot.types.InlineKeyboardButton(text='Вперед', callback_data=forward))

            elif type == "finish":
                if start > -1 and start < 1:
                    markup.add(telebot.types.InlineKeyboardButton(text='Назад', callback_data=back),
                               telebot.types.InlineKeyboardButton(text='Вперед', callback_data=forward))
                else:
                    markup.add(telebot.types.InlineKeyboardButton(text='Назад', callback_data=back),
                               telebot.types.InlineKeyboardButton(text='👍', callback_data="true"),
                               telebot.types.InlineKeyboardButton(text='👎', callback_data="false"),
                               telebot.types.InlineKeyboardButton(text='Вперед', callback_data=forward))

            date = datetime.utcfromtimestamp(int(data[7])).strftime('%Y-%m-%d %H:%M:%S')
            info += "\n\n" \
                    "*%s*\n\n" \
                    "%s\n\n" \
                    "Дата создания: %s\n\n" \
                    "Автор: %s" % (data[1], data[2], date, data[6])
        else:
            if start == 0:
                info = '*На данный момент нет заявок в системе. Но вы можете стать первым!*'
                markup = telebot.types.ReplyKeyboardMarkup(True)
                markup.row('Главная', 'Список заявок', "Добавить заявку")
            else:
                info = '*Заявки закончились*'
                markup = telebot.types.ReplyKeyboardMarkup(True)
                markup.row('Главная', 'Список заявок', "Добавить заявку")


    bot.send_message(message.chat.id, text=info, reply_markup=markup, parse_mode="Markdown")

# Create new task
def createTask(message):
    info = "Нашли проблему? Поделитесь с нами! Напишите заголовок проблемы:"
    keyboard = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, info, reply_markup=keyboard)
    bot.register_next_step_handler(message, doTaskS1)

# Task step 1
def doTaskS1(message):
    text = message.text
    info = "Теперь напишите описание проблемы:"
    bot.send_message(message.chat.id, info)
    bot.register_next_step_handler(message, doTaskS2, text)

# Task step 2
def doTaskS2(message, title):
    text = message.text
    info = "Хотите указать себя как автора заявки? (Да/Нет)"
    bot.send_message(message.chat.id, info)
    bot.register_next_step_handler(message, doTaskS3, title, text)

# Task step 3
def doTaskS3(message, title, description):
    author = message.text.lower()
    if author == "да":
        author = "@%s" % message.from_user.username
    else:
        author = "Аноним"

    title = re.sub('\'', '\\\'', title)
    description = re.sub('\'', '\\\'', description)

    query = "INSERT INTO tasks VALUE(NULL, '%s', '%s', '%s', '-', '%s', '%s', '%s', '%s');" % (title, description, 'new', message.chat.id, author, int(datetime.now().timestamp()), '')
    cursor.execute(query)
    db.commit()

    id = cursor.lastrowid

    info = "Заявка успешно добавлена и отправлена на модерацию!"
    cursor.execute('SELECT chatId FROM users WHERE type="admin"')
    data = cursor.fetchone()

    # Send message to admin about task
    adminInfo = "*Пользователь предложил новый запрос*\n\n" \
                "*%s*\n" \
                "%s\n" % (title, description)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton(text='Удалить', callback_data="admin:task:del:%s" % id),
               telebot.types.InlineKeyboardButton(text='Добавить', callback_data="admin:task:accept:%s" % id))
    bot.send_message(data[0], adminInfo, reply_markup=markup, parse_mode="Markdown")

    # Send message to user
    bot.send_message(message.chat.id, info)
    showMain(message)

# Get weather data
def getWeather(message):
    data = urllib.request.urlopen("http://api.openweathermap.org/data/2.5/weather?q=Odessa&appid=%s&units=metric&lang=ru" % config.WEATHER_API).read()
    output = json.loads(data)

    mainWeather = output['main']
    secWeather = output['weather'][0]

    info = "*Текущая погода в Одессе*\n" \
           "Температура: %s °C\n" \
           "Ощущается: %s °C\n" \
           "Влажность: %s%%\n" \
           "Скорость ветра: %s м/с\n" \
           "Осадки: %s" % (mainWeather['temp'], mainWeather['feels_like'], mainWeather['humidity'],
                                   output['wind']['speed'], secWeather['description'])

    bot.send_message(message.chat.id, text=info, parse_mode="Markdown")