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
    "Нефтегазовое дело": {
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
bot.set_my_commands([
    telebot.types.BotCommand("start", "Начать регистрацию"),
    telebot.types.BotCommand("menu", "Главное меню"),
    telebot.types.BotCommand("status", "Успеваемость и баллы"),
    telebot.types.BotCommand("add_grade", "Добавить или изменить оценку"),
    telebot.types.BotCommand("set_debts", "Указать количество долгов"),
    telebot.types.BotCommand("card", "Карточка студента"),
    telebot.types.BotCommand("grades", "Показать оценки"),
    telebot.types.BotCommand("university", "Информация об университете"),
    telebot.types.BotCommand("achievements", "Просмотр своих достижений"),
    telebot.types.BotCommand("admin", "Список всех студентов (только для админов)")
])



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
/university — университет FAQ
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


# главное меню педики йобана)

@bot.message_handler(commands=['menu'])
def menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Успеваемость", callback_data="status"),
        types.InlineKeyboardButton("📘 Оценки", callback_data="grades"),
        types.InlineKeyboardButton("✏️ Добавить", callback_data="add_grade"),
        types.InlineKeyboardButton("❗ Долги", callback_data="set_debts"),
        types.InlineKeyboardButton("📄 Карточка", callback_data="card"),
        types.InlineKeyboardButton("⏰ Напоминания", callback_data="reminders"),  # Новая кнопка
        types.InlineKeyboardButton("🏛 Университет FAQ", callback_data="university")
    )
    bot.send_message(message.chat.id, "📲 Главное меню:", reply_markup=markup)

# ХЗ ДИПСОН СКАЗАЛ СЮДА ЭТО ВСТАВИТЬ, ИМЕННО ПЕРЕД СЛЕДУЮЩИМ КОЛЛБЭКОМ

@bot.callback_query_handler(func=lambda call: call.data == "reminders")
def handle_reminders(call):
    user_id = str(call.message.chat.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("➕ Добавить напоминание", callback_data="add_reminder"),
        types.InlineKeyboardButton("📋 Мои напоминания", callback_data="list_reminders")
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="⏰ Управление напоминаниями:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    try:
        print(f"DEBUG: Нажата кнопка: {call.data}")  # Для отладки
    
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
        elif call.data == "university":  # Обработка кнопки из главного меню
            university_info(call.message)
        elif call.data.startswith('uni_'):  # Обработка кнопок университета
            handle_university_buttons(call)
            
        bot.answer_callback_query(call.id)  # Подтверждение нажатия
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка. Попробуйте снова.")



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



@bot.message_handler(commands=['university'])
def university_info(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("Контакты преподавателей", callback_data="uni_contacts"),
        types.InlineKeyboardButton("Расписание звонков", callback_data="uni_schedule"),
        types.InlineKeyboardButton("Адреса корпусов", callback_data="uni_map"),
        types.InlineKeyboardButton("Правила пересдач", callback_data="uni_retakes"),
        types.InlineKeyboardButton("Шаблоны заявлений", callback_data="uni_templates")
    ]
    markup.add(*buttons)
    
    bot.send_message(
        message.chat.id,
        "🏛 Университет FAQ - выберите раздел:",
        reply_markup=markup
    )


def handle_university_buttons(call):
    try:
        # Удаляем клавиатуру после нажатия
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )
        
        if call.data == "uni_contacts":
            text = "📞 Контакты преподавателей:\n\n1. Панченко Наталья Борисовна: +7-922-486-62-05\n2. Заичко Маргарита Васильевна: +7-904-492-50-50"
        
        elif call.data == "uni_schedule":
            text = "🕒 Расписание звонков:\n\n1 пара: 08:00 - 09:35\n2 пара: 09:45 - 11:20\n3 пара: 11:30 - 13:05\n4 пара: 13:45 - 15:20\n5 пара: 15:30 - 17:05\n6 пара: 17:15 - 18:50\n7 пара: 19:00 - 20:25\n8 пара: 20:35 - 22:00"
        
        elif call.data == "uni_map":
            text = """🏛 Адреса корпусов:

Корпус №1 (Учебно-лабораторный): г. Тюмень, ул. Володарского, 38
Корпус №1 А (Учебно-лабораторный): г. Тюмень, ул. Республики, 49/3
Корпус №1 Б (Учебный): г. Тюмень, ул. Республики, 47
Корпус №2 (Учебно-лабораторный): г. Тюмень, ул. Мельникайте, 72
Корпус №3 (Учебно-лабораторный): г. Тюмень, ул. 50 лет Октября, 38
Корпус №4 (Учебно-лабораторный): г. Тюмень, ул. Володарского, 56
Корпус №5 (Учебный): г. Тюмень, ул. Мельникайте, 72, корпус 1
Корпус №6 (Учебно-лабораторный): г. Тюмень, ул. Киевская, 52
Корпус №7 (Учебный): г. Тюмень, ул. Мельникайте, 70
Корпус №8 (Учебно-лабораторный): г. Тюмень, ул. Луначарского, 2
Корпус №8/1 (Инженерно-лабораторный): г. Тюмень, ул. Луначарского, 2, корпус 1
Корпус №8/2 (Учебный): г. Тюмень, ул. Луначарского, 2, корпус 2
Корпус №8/3 (Учебный): г. Тюмень, ул. Луначарского, 2, корпус 3
Корпус №8/4 (Спортивный зал): г. Тюмень, ул. Луначарского, 2, корпус 4
Корпус №8/5 (СК "Зодчий"): г. Тюмень, ул. Луначарского, 2, корпус 5
Корпус №8/6 (Учебно-лабораторный): г. Тюмень, ул. Луначарского, 2, корпус 6
Корпус №9 (Учебно-лабораторный): г. Тюмень, ул. Луначарского, 4
Корпус №10 (Учебный): г. Тюмень, ул. Энергетиков, 44, корпус 1
Корпус №11 (Учебный): г. Тюмень, ул. Энергетиков, 44
Корпус №12 (Учебный): г. Тюмень, ул. Бабарынка, 20 б
Корпус №13 (Учебный): г. Тюмень, ул. Холодильная, 85
Корпус №14 (Учебный): г. Тюмень, ул. Холодильная, 85, строение 1
Корпус №15 (Учебный): г. Тюмень, ул. 50 лет ВЛКСМ, 45 а, стр. 1
Корпус №16 (Учебный): г. Тюмень, ул. 50 лет Октября, 62
Корпус №17 (Учебный): г. Тюмень, ул. Киевская, 78, корпус 1
Корпус №18 (Учебные мастерские): г. Тюмень, ул. Мало-Загородная, 17"""
        elif call.data == "uni_retakes":
            text = "📝 Правила пересдач:\n\n1. Пересдача проводится 1 раз за семестр\n2. Необходимо договориться с преподавателем о дате, времени, месте (возможно вам придётся получить дополнительный задания)\n3. Максимальная оценка при пересдаче - 5"
        
        elif call.data == "uni_templates":
            text = "📄 Шаблоны заявлений:\n\nДержите файл!"
            try:
                with open('Формы представлений для подачи заявлений на повышенную стипендию.docx', 'rb') as doc:
                    bot.send_document(call.message.chat.id, doc, caption="Форма заявления")
            except Exception as e:
                print(f"Ошибка: {e}")
                text = "⚠️ Файл не найден"
        
        bot.send_message(call.message.chat.id, text)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(call.message.chat.id, "⚠️ Ошибка сервера")




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
