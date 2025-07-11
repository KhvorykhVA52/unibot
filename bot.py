import telebot
import math
import requests
from telebot import types
from config import TOKEN
from database import *
import sqlite3
import threading
import time

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

bot = telebot.TeleBot(TOKEN)

# Вспомогательные функции
def add_back_button(markup, back_to):
    """Добавляет кнопку Назад в указанную клавиатуру"""
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=back_to))

def send_with_back(message, text, back_to):
    """Отправляет сообщение с кнопкой Назад"""
    markup = types.InlineKeyboardMarkup()
    add_back_button(markup, back_to)
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Обработчики команд
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

    student_names = get_students_by_group(faculty, specialty, group_name)
    if not student_names:
        bot.send_message(message.chat.id, "⚠️ В этой группе пока нет студентов в базе. Обратись к администратору.")
        return

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
/university — FAQ по университету
/achievements — посмотреть свои достижения  
/logout - выйти из аккаунта

"""
    bot.send_message(message.chat.id, commands_text)

@bot.message_handler(commands=['menu'])
def show_main_menu(chat_id_or_message):
    """Показывает главное меню"""
    if isinstance(chat_id_or_message, types.CallbackQuery):
        chat_id = chat_id_or_message.message.chat.id
        try:
            bot.delete_message(chat_id, chat_id_or_message.message.message_id)
        except:
            pass
    else:
        chat_id = chat_id_or_message.chat.id if hasattr(chat_id_or_message, 'chat') else chat_id_or_message

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Успеваемость", callback_data="status"),
        types.InlineKeyboardButton("📘 Оценки", callback_data="grades"),
        types.InlineKeyboardButton("✏️ Добавить", callback_data="add_grade"),
        types.InlineKeyboardButton("❗ Долги", callback_data="set_debts"),
        types.InlineKeyboardButton("📄 Карточка", callback_data="card"),
        types.InlineKeyboardButton("⏰ Напоминания", callback_data="reminders"),
        types.InlineKeyboardButton("💪 Мотивация", callback_data="motivation"),  
        types.InlineKeyboardButton("🏛 Университет FAQ", callback_data="university")
    )
    bot.send_message(chat_id, "📲 Главное меню:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def back_to_menu(call):
    show_main_menu(call)

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

    if avg >= 90:
        prediction = "Отлично (5)"
    elif avg >= 75:
        prediction = "Хорошо (4)"
    elif avg >= 60:
        prediction = "Удовлетворительно (3)"
    else:
        prediction = "Неуд (2) — риск отчисления высок"

    critical_subjects = [f"❗ {subj}: {score} баллов" for subj, score in grades.items() if score < 60]
    critical_text = "\n".join(critical_subjects) or "Нет критических предметов"

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
    send_with_back(message, text, "menu")

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

    send_with_back(message, f"📘 Твои оценки:\n{grades_text}", "menu")

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

        result = "\n".join([f"{subj}: {score} баллов" for subj, score in updates.items()])
        send_with_back(message, f"✅ Добавлены/обновлены оценки:\n{result}", "menu")

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
        send_with_back(message, f"Обновлено: теперь у тебя {debts} долгов.", "menu")
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
    send_with_back(message, text, "menu")

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

    send_with_back(message, report, "menu")

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
    add_back_button(markup, "menu")
    
    bot.send_message(
        message.chat.id,
        "🏛 Университет FAQ - выберите раздел:",
        reply_markup=markup
    )

# Обработчики callback-запросов
@bot.callback_query_handler(func=lambda call: call.data == "reminders")
def handle_reminders(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("➕ Добавить напоминание", callback_data="add_reminder"),
        types.InlineKeyboardButton("📋 Мои напоминания", callback_data="list_reminders")
    )
    add_back_button(markup, "menu")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="⏰ Управление напоминаниями:",
        reply_markup=markup
    )

def handle_university_buttons(call):
    try:
        if call.data == "uni_contacts":
            text = "📞 Контакты преподавателей:\n\n1. Панченко Наталья Борисовна: +7-922-486-62-05\n2. Заичко Маргарита Васильевна: +7-904-492-50-50"
            markup = types.InlineKeyboardMarkup()
            add_back_button(markup, "university")
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

        elif call.data == "uni_schedule":
            text = (
                "🕒 Расписание звонков:\n\n"
                "1 пара: 08:00 - 09:35\n"
                "2 пара: 09:45 - 11:20\n"
                "3 пара: 11:30 - 13:05\n"
                "4 пара: 13:45 - 15:20\n"
                "5 пара: 15:30 - 17:05\n"
                "6 пара: 17:15 - 18:50\n"
                "7 пара: 19:00 - 20:25\n"
                "8 пара: 20:35 - 22:00"
            )
            markup = types.InlineKeyboardMarkup()
            add_back_button(markup, "university")
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

        elif call.data == "uni_map":
            buildings = get_all_buildings()
            if buildings:
                markup = types.InlineKeyboardMarkup(row_width=1)
                for i, (name, _) in enumerate(buildings):
                    markup.add(types.InlineKeyboardButton(name, callback_data=f"bld_{i}"))
                add_back_button(markup, "university")
                bot.send_message(call.message.chat.id, "🏛 Выберите корпус:", reply_markup=markup)
            else:
                markup = types.InlineKeyboardMarkup()
                add_back_button(markup, "university")
                bot.send_message(call.message.chat.id, "⚠️ Список корпусов пока не заполнен.", reply_markup=markup)

        elif call.data == "uni_retakes":
            text = (
                "📝 Правила пересдач:\n\n"
                "1. Пересдача проводится 1 раз за семестр\n"
                "2. Необходимо договориться с преподавателем о дате, времени, месте\n"
                "3. Максимальная оценка при пересдаче — 5"
            )
            markup = types.InlineKeyboardMarkup()
            add_back_button(markup, "university")
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

        elif call.data == "uni_templates":
            try:
                with open('zayavlenie.docx', 'rb') as doc:
                    bot.send_document(call.message.chat.id, doc, caption="📄 Вот держи!")
                markup = types.InlineKeyboardMarkup()
                add_back_button(markup, "university")
                bot.send_message(call.message.chat.id, "⬅️ Вернуться в раздел FAQ:", reply_markup=markup)
            except Exception as e:
                print(f"Ошибка при отправке документа: {e}")
                markup = types.InlineKeyboardMarkup()
                add_back_button(markup, "university")
                bot.send_message(call.message.chat.id, "⚠️ Файл не найден", reply_markup=markup)

        elif call.data.startswith("bld_"):
            index = int(call.data.split("_")[1])
            buildings = get_all_buildings()
            if 0 <= index < len(buildings):
                name, address = buildings[index]
                text = f"🏛 <b>{name}</b>\n📍 {address}"
                markup = types.InlineKeyboardMarkup()
                add_back_button(markup, "uni_map")
                bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)
            else:
                markup = types.InlineKeyboardMarkup()
                add_back_button(markup, "uni_map")
                bot.send_message(call.message.chat.id, "⚠️ Корпус не найден.", reply_markup=markup)

    except Exception as e:
        print(f"[ERROR] В обработчике university_buttons: {e}")
        bot.send_message(call.message.chat.id, "⚠️ Ошибка сервера")

@bot.message_handler(commands=['quote'])
def send_quote(message):
    try:
        url = "https://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang=ru"
        response = requests.get(url, timeout=5)
        data = response.json()

        quote = data.get("quoteText", "Цитата недоступна.").strip()
        author = data.get("quoteAuthor", "Неизвестный автор").strip()

        bot.send_message(message.chat.id, f"💬 <b>{quote}</b>\n— <i>{author}</i>", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Ошибка при получении цитаты.")
        print(f"[ERROR] Цитата: {e}")

# --- ЦИТАТА ---
def send_quote(message):
    try:
        response = requests.get("https://api.quotable.io/random", timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            quote = data['content']
            author = data['author']
            text = f"💬 {quote}\n— {author}"
        else:
            text = "⚠️ Не удалось получить цитату. Попробуй позже."
        send_with_back(message, text, "motivation")
    except Exception as e:
        print(f"[ERROR] Цитата: {e}")
        bot.send_message(message.chat.id, "⚠️ Ошибка при получении цитаты.")

def start_pomodoro(message):
    try:
        bot.send_message(message.chat.id, "⏱ Pomodoro запущен: 25 минут фокусировки!\nЯ напомню, когда время истечёт.")
        threading.Timer(1500, lambda: bot.send_message(message.chat.id, "🔔 Время вышло! Сделай 5-минутный перерыв.")).start()
    except Exception as e:
        print(f"[ERROR] Pomodoro: {e}")
        bot.send_message(message.chat.id, "⚠️ Не удалось запустить таймер.")

def handle_motivation(call):
    try:
        text = "💪 *Мотивация*\n\nВыберите действие:"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🍅 Pomodoro-таймер", callback_data="pomodoro"),
            types.InlineKeyboardButton("🏅 Ачивки", callback_data="achievements"),
            types.InlineKeyboardButton("💬 Цитата дня", callback_data="quote"),
        )
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="menu"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"[ERROR] в handle_motivation: {e}")
        bot.send_message(call.message.chat.id, "⚠️ Ошибка при открытии раздела мотивации.")

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    try:
        try:
            bot.answer_callback_query(call.id)
        except Exception as e:
            print(f"[ERROR] Не удалось отправить answer_callback_query: {e}")

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
        elif call.data == "reminders":
            handle_reminders(call)
        elif call.data == "university":
            university_info(call.message)
        elif call.data.startswith("bld_") or call.data.startswith("uni_"):
            handle_university_buttons(call)
        elif call.data == "menu":
            show_main_menu(call)
        elif call.data == "motivation":
            handle_motivation(call)
        elif call.data == "quote":
            send_quote(call.message)
        elif call.data == "pomodoro":
            start_pomodoro(call.message)
        elif call.data == "quote":
            send_quote(call.message)
        elif call.data == "achievements":
            achievements(call.message)

            
    except Exception as e:
        print(f"[ERROR] в handle_all_callbacks: {e}")
        bot.answer_callback_query(call.id, "⚠️ Ошибка. Попробуйте снова.")

@bot.message_handler(commands=['logout'])
def logout(message):
    user_id = str(message.chat.id)
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE students SET id = NULL, active = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "🗑 Ты вышел. Чтобы начать заново, напиши /start.")

@bot.message_handler(commands=['achievements'])
def achievements(message):
    user_id = str(message.chat.id)
    student = get_student(user_id)
    if not student:
        bot.send_message(message.chat.id, "❗ Ты не зарегистрирован.")
        return

    ach_list = get_achievements(user_id)
    if not ach_list:
        send_with_back(message, "🏅 У тебя пока нет достижений. Подтяни оценки — и будут!", "motivation")
    else:
        text = "🏅 Твои достижения:\n" + "\n".join([f"✅ {a}" for a in ach_list])
        send_with_back(message, text, "motivation")


# Фоновые задачи
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

                if updates:
                    message = "📢 Обновление оценок:\n" + "\n".join(updates)
                    try:
                        bot.send_message(user_id, message)
                    except Exception as e:
                        print(f"[ERROR] Не удалось отправить сообщение студенту ID {user_id}: {e}")
                    update_last_grades(user_id, current_grades)

        except Exception as e:
            print(f"[ERROR] В потоке обновления оценок: {e}")

        time.sleep(60)

threading.Thread(target=check_for_grade_updates, daemon=True).start()

print("[INFO] Бот запущен и ждёт команды")
bot.polling()