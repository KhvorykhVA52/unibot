import telebot
from telebot import types
from config import TOKEN
from database import *
import sqlite3

init_db()

faculties = {
    "ВШЦТ": {
        "Информационная безопасность компьютерных систем и сетей": ["ИБКСб 24-1", "ИБКСб 23-1"],
        "Автоматизированные системы обработки информации и управления": ["АСОиУБ-24-1", "АСОиУБ-23-1"]
    },
    "Нефтегазовые дело": {
        "Автоматизация технологических процессов и производств в нефтяной и газовой промышленности": ["АТП-21", "ЭЭ-22"],
        "Нефтегазовое дело": ["НДБ-24", "НДБ-23"]
    },
    "ИТ": {
        "Моделирование механических систем и процессов": ["ММСП-24", "ММСП-23"],
    },
    "ИПТИ": {
        " Приборы, методы контроля качества и диагностики"  : ["ПККД-24", "ПККД-23"],
    },
    "СТРОИН" : {
        "Промышленное и гражданское строительство": ["ПГС-24", "ПГС-23"],
    },
}

ADMIN_IDS = [
    "1592890429", "1116477607", "6499953001",
    "564380150", "1025247272", "843344460"
]

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)

    if student_exists(user_id):
        bot.send_message(message.chat.id, "✅ Ты уже зарегистрирован.\nНапиши /menu чтобы продолжить.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for fac in faculties.keys():
        markup.add(types.KeyboardButton(fac))

    msg = bot.send_message(message.chat.id, "Привет👋, Выбери факультет:", reply_markup=markup)
    bot.register_next_step_handler(msg, select_faculty)

def select_faculty(message):
    faculty = message.text.strip()
    if faculty not in faculties:
        bot.send_message(message.chat.id, "❗ Неверный факультет. Попробуй снова: /start")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for spec in faculties[faculty].keys():
        markup.add(types.KeyboardButton(spec))

    msg = bot.send_message(message.chat.id, "📘 Выбери специальность:", reply_markup=markup)
    bot.register_next_step_handler(msg, select_specialty, faculty)

def select_specialty(message, faculty):
    specialty = message.text.strip()
    if specialty not in faculties[faculty]:
        bot.send_message(message.chat.id, "❗ Неверная специальность. Попробуй снова: /start")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for group in faculties[faculty][specialty]:
        markup.add(types.KeyboardButton(group))

    msg = bot.send_message(message.chat.id, "🧑‍🎓 Выбери свою группу:", reply_markup=markup)
    bot.register_next_step_handler(msg, select_group, faculty, specialty)

def select_group(message, faculty, specialty):
    group_name = message.text.strip()
    if group_name not in faculties[faculty][specialty]:
        bot.send_message(message.chat.id, "❗ Неверная группа. Попробуй снова: /start")
        return

    msg = bot.send_message(message.chat.id, "✍️ Введи своё ФИО:")
    bot.register_next_step_handler(msg, finish_registration, faculty, specialty, group_name)

def finish_registration(message, faculty, specialty, group_name):
    user_id = str(message.chat.id)
    name = message.text.strip()
    add_student(user_id, name, faculty, specialty, group_name)
    bot.send_message(message.chat.id, f"✅ Добро пожаловать, {name}!\nТы зарегистрирован.")
    bot.send_message(message.chat.id, "Теперь можешь использовать команду /menu для работы с ботом.")


@bot.message_handler(commands=['status'])
def status(message):
    user_id = str(message.chat.id)
    student = get_student(user_id)

    if not student:
        bot.send_message(message.chat.id, "❗ Ты не зарегистрирован. Напиши /start.")
        return

    name = student["name"]
    grades = student["grades"]
    debts = student["debts"]
    avg = round(sum(grades.values()) / len(grades), 2) if grades else 0.0
    risk = min(100, debts * 25)
    grades_text = "\n".join([f"{subj}: {score} баллов" for subj, score in grades.items()]) or "Нет оценок"

    text = f"""👤 {name}
🏛 Факультет: {student["faculty"]}
📘 Специальность: {student["specialty"]}
🧑‍🎓 Группа: {student["group"]}

📚 Успеваемость:
{grades_text}

📈 Средний балл: {avg}
❗ Долги: {debts}
🔥 Риск отчисления: {risk}%
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['grades'])
def grades(message):
    user_id = str(message.chat.id)
    student = get_student(user_id)

    if not student:
        bot.send_message(message.chat.id, "❗ Ты не зарегистрирован.")
        return

    grades = student["grades"]
    if grades:
        grades_text = "\n".join([f"{subj}: {score} баллов" for subj, score in grades.items()])
    else:
        grades_text = "Нет оценок"

    bot.send_message(message.chat.id, f"📘 Твои оценки:\n{grades_text}")

@bot.message_handler(commands=['add_grade'])
def add_grade(message):
    msg = bot.send_message(message.chat.id, "✍️ Введи предмет и баллы через запятую:")
    bot.register_next_step_handler(msg, save_grade)

def save_grade(message):
    try:
        user_id = str(message.chat.id)
        student = get_student(user_id)
        if not student:
            bot.send_message(message.chat.id, "❗ Ты не зарегистрирован.")
            return

        subject, score = message.text.split(",")
        grades = student["grades"]
        grades[subject.strip()] = int(score.strip())
        update_grades(user_id, grades)
        bot.send_message(message.chat.id, f"✅ Оценка по '{subject.strip()}' обновлена.")
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка! Формат: Предмет, Баллы")

@bot.message_handler(commands=['set_debts'])
def set_debts(message):
    msg = bot.send_message(message.chat.id, "Сколько у тебя долгов? Введи число:")
    bot.register_next_step_handler(msg, save_debts)

def save_debts(message):
    try:
        user_id = str(message.chat.id)
        student = get_student(user_id)
        if not student:
            bot.send_message(message.chat.id, "❗ Ты не зарегистрирован.")
            return

        debts = int(message.text.strip())
        update_debts(user_id, debts)
        bot.send_message(message.chat.id, f"Обновлено: теперь у тебя {debts} долгов.")
    except:
        bot.send_message(message.chat.id, "⚠️ Ошибка! Введи число.")

@bot.message_handler(commands=['card'])
def card(message):
    user_id = str(message.chat.id)
    student = get_student(user_id)

    if not student:
        bot.send_message(message.chat.id, "❗ Ты не зарегистрирован.")
        return

    name = student["name"]
    grades = student["grades"]
    debts = student["debts"]
    avg = round(sum(grades.values()) / len(grades), 2) if grades else 0.0
    risk = min(100, debts * 25)
    grades_text = "\n".join([f"{subj}: {score} баллов" for subj, score in grades.items()]) or "Нет оценок"

    text = f"""🎓 Карточка студента

👤 ФИО: {name}
🆔 ID: {user_id}

📚 Успеваемость:
{grades_text}

📈 Средний балл: {avg}
❗ Долги: {debts}
🔥 Риск отчисления: {risk}%
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = str(message.chat.id)

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа к админ-панели.")
        return

    report = "📋 Список студентов:\n\n"
    students = get_all_students()

    for student in students:
        name = student["name"]
        uid = student["id"]
        grades = student["grades"]
        debts = student["debts"]
        avg = round(sum(grades.values()) / len(grades), 2) if grades else 0.0
        risk = min(100, debts * 25)

        report += f"""👤 {name}
ID: {uid}
📈 Средний балл: {avg}
❗ Долги: {debts} | 🔥 Риск: {risk}%\n\n"""

    bot.send_message(message.chat.id, report)

@bot.message_handler(commands=['menu'])
def menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Успеваемость", callback_data="status"),
        types.InlineKeyboardButton("📘 Оценки", callback_data="grades"),
        types.InlineKeyboardButton("✏️ Добавить", callback_data="add_grade"),
        types.InlineKeyboardButton("❗ Долги", callback_data="set_debts"),
        types.InlineKeyboardButton("📄 Карточка", callback_data="card")
    )
    bot.send_message(message.chat.id, "📲 Главное меню:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    if call.data == "status":
        status(call.message)
    elif call.data == "grades":
        grades(call.message)
    elif call.data == "add_grade":
        add_grade(call.message)
    elif call.data == "set_debts":
        set_debts(call.message)
    elif call.data == "card":
        card(call.message)

@bot.message_handler(commands=['delete_me'])
def delete_me(message):
    import sqlite3
    user_id = str(message.chat.id)
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "🗑 Ты удалён из базы. Напиши /start чтобы зарегистрироваться заново.")
bot.polling()
