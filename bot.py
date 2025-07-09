import telebot
import math
from telebot import types
from config import TOKEN
from database import *
import sqlite3

init_db()

faculties = {
    "ВШЦТ": {
        "Информационная безопасность компьютерных систем и сетей": ["ИБКС-24-1", "ИБКС-23"],
        "Автоматизированные системы обработки информации и управления": ["АСОиУБ-24-1", "АСОиУБ-23"]
    },
    "Нефтегазовые дело": {
        "Автоматизация технологических процессов и производств в нефтяной и газовой промышленности": ["АТП-21", "ЭЭ-22"],
        "Нефтегазовое дело": ["НДБ-24", "НДБ-23"]
    }
}

ADMIN_IDS = [
    "1592890429", "1116477607", "6499953001",
    "564380150", "1025247272", "843344460"
]

import threading
import time

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

    msg = bot.send_message(message.chat.id, "🏛 Выбери факультет:", reply_markup=markup)
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

    # Получаем список студентов из базы
    student_names = get_students_by_group(faculty, specialty, group_name)
    if not student_names:
        bot.send_message(message.chat.id, "⚠️ В этой группе пока нет студентов в базе. Обратись к администратору.")
        return

    # Отправляем список ФИО для выбора
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for name in student_names:
        markup.add(types.KeyboardButton(name))

    msg = bot.send_message(message.chat.id, "👤 Выбери своё ФИО из списка:", reply_markup=markup)
    bot.register_next_step_handler(msg, assign_identity, faculty, specialty, group_name)

def assign_identity(message, faculty, specialty, group_name):
    user_id = str(message.chat.id)
    name = message.text.strip()
    assign_user_id_to_student(user_id, name, faculty, specialty, group_name)

    bot.send_message(message.chat.id, f"""✅ Добро пожаловать, {name}!
Ты зарегистрирован.""")


    commands_text = """
📌 Теперь ты можешь использовать команды:

/menu — открыть главное меню
/status — посмотреть успеваемость
/grades — список оценок
/add_grade — добавить или изменить оценку
/set_debts — указать количество долгов
/card — карточка студента
/admin — список всех студентов (только для админов)
"""
    bot.send_message(message.chat.id, commands_text)

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
    msg = bot.send_message(message.chat.id, "✍️ Введи предмет и баллы через запятую:\nНапример: Физика, 85")
    bot.register_next_step_handler(msg, save_grade)

def save_grade(message):
    try:
        user_id = str(message.chat.id)
        student = get_student(user_id)

        if not student:
            bot.send_message(message.chat.id, "❗ Ты не зарегистрирован.")
            return

        text = message.text.strip()

        # Пример: "Физика, 78. Алгебра, 99. История, 85"
        items = text.split(".")
        updates = {}

        for item in items:
            if "," not in item:
                continue
            subject, score = item.split(",", 1)
            subject = subject.strip()
            score = int(score.strip())
            updates[subject] = score

        if not updates:
            raise ValueError("Нет валидных предметов")

        grades = student["grades"]
        grades.update(updates)
        update_grades(user_id, grades)

        # Формируем ответ
        result = "\n".join([f"{subj}: {score} баллов" for subj, score in updates.items()])
        bot.send_message(message.chat.id, f"✅ Добавлены/обновлены оценки:\n{result}")

    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Ошибка! Формат: Физика, 78. Алгебра, 99.")
        print(f"[DEBUG] Ошибка в save_grade: {e}")




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

def check_for_grade_updates():
    while True:
        try:
            students = get_all_students()
            for student in students:
                user_id = student['id']
                if not user_id:
                    continue

                current_grades = student["grades"]
                last_grades = student.get("last_grades", {}) or {}

                if not last_grades:
                    update_last_grades(user_id, current_grades)
                    continue

                updates = []
                for subject, new_score in current_grades.items():
                    old_score = last_grades.get(subject)
                    if old_score is not None and new_score != old_score:
                        updates.append(f"{subject}: было {old_score} → стало {new_score}")

                print(f"[DEBUG] {student['name']} — сравниваем оценки:")
                print(f"grades      : {current_grades}")
                print(f"last_grades : {last_grades}")

                if updates:
                    message = "📢 Обновление оценок:\n" + "\n".join(updates)
                    try:
                        bot.send_message(user_id, message)
                        print(f"[OK] Уведомление отправлено студенту ID {user_id}.")
                    except Exception as e:
                        print(f"[ERROR] Не удалось отправить сообщение студенту ID {user_id}: {e}")
                    update_last_grades(user_id, current_grades)

        except Exception as e:
            print(f"[ERROR] В потоке обновления оценок: {e}")

        time.sleep(60)

threading.Thread(target=check_for_grade_updates, daemon=True).start()

@bot.message_handler(commands=['status'])
def status(message):
    user_id = str(message.chat.id)
    print(f"[DEBUG] Обработчик /status: user_id = {user_id}")

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

    # прогноз оценки
    if avg >= 90:
        prediction = "Отлично (5)"
    elif avg >= 75:
        prediction = "Хорошо (4)"
    elif avg >= 60:
        prediction = "Удовлетворительно (3)"
    else:
        prediction = "Неуд (2) — риск отчисления высок"

    # критические предметы
    critical_subjects = [f"❗ {subj}: {score} баллов" for subj, score in grades.items() if score < 60]
    critical_text = "\n".join(critical_subjects) or "Нет критических предметов"

    # прогресс-бар (цель — 85 баллов)
    goal = 85
    filled = math.floor(avg / goal * 5)
    bar = "▰" * filled + "▱" * (5 - filled)
    progress_line = f"🔄 Прогресс к цели: {bar} {avg} / {goal}"

    text = f"""👤 {name}
🏛 Факультет: {student["faculty"]}
📘 Специальность: {student["specialty"]}
🧑‍🎓 Группа: {student["group"]}

📊 Моя Успеваемость
   ├─ Текущие баллы
{grades_text}
   ├─ Прогноз итоговой оценки: {prediction}
   ├─ Критические предметы:
{critical_text}
   └─ {progress_line}

📈 Средний балл: {avg}
❗ Долги: {debts}
🔥 Риск отчисления: {risk}%
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['achievements'])
def achievements(message):
    user_id = str(message.chat.id)
    student = get_student(user_id)
    if not student:
        bot.send_message(message.chat.id, "❗ Ты не зарегистрирован. Напиши /start.")
        return

    achievements_list = get_achievements(user_id)
    if not achievements_list:
        bot.send_message(message.chat.id, "🏅 У тебя пока нет достижений. Заработай их, повышая свои оценки!")
    else:
        text = "🏅 Твои достижения:\n" + "\n".join([f"✅ {a}" for a in achievements_list])
        bot.send_message(message.chat.id, text)

print("[INFO] Бот запущен и ждёт команды")
bot.polling()
