ADMIN_IDS = ["1592890429","1116477607", "6499953001", "564380150","1025247272", "843344460" ]  # Список ID администраторов]
import telebot
import json
from telebot import types
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

def load_data():
    with open("data.json", "r", encoding="utf-8") as file:
        return json.load(file)

def calculate_risk(student_data):
    debts = student_data.get("debts", 0)
    risk = min(100, debts * 25)  
    return risk

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    data = load_data()

    if user_id in data["students"]:
        bot.send_message(message.chat.id, "👋 Привет! Ты уже зарегистрирован.\nНапиши /status, чтобы посмотреть успеваемость.")
    else:
        bot.send_message(message.chat.id, f"👤 Твой ID: {user_id}")
        msg = bot.send_message(message.chat.id, "📝 Напиши своё ФИО, чтобы зарегистрироваться:")
        bot.register_next_step_handler(msg, register_student)

@bot.message_handler(commands=['menu'])
def menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn1 = types.InlineKeyboardButton("📊 Успеваемость", callback_data="status")
    btn2 = types.InlineKeyboardButton("📘 Оценки", callback_data="grades")
    btn3 = types.InlineKeyboardButton("✏️ Добавить", callback_data="add_grade")
    btn4 = types.InlineKeyboardButton("❗ Долги", callback_data="set_debts")
    btn5 = types.InlineKeyboardButton("📄 Карточка", callback_data="card")

    markup.add(btn1, btn2, btn3, btn4, btn5)

    bot.send_message(message.chat.id, "📲 Главное меню:\nВыбери действие:", reply_markup=markup)


       
@bot.message_handler(commands=['menu_inline'])
def menu_inline(message):
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn1 = types.InlineKeyboardButton("📊 Успеваемость", callback_data="status")
    btn2 = types.InlineKeyboardButton("📘 Оценки", callback_data="grades")
    btn3 = types.InlineKeyboardButton("✏️ Добавить", callback_data="add_grade")
    btn4 = types.InlineKeyboardButton("❗ Долги", callback_data="set_debts")
    btn5 = types.InlineKeyboardButton("📄 Карточка", callback_data="card")

    markup.add(btn1, btn2, btn3, btn4, btn5)

    bot.send_message(message.chat.id, "📲 Выбери действие:", reply_markup=markup)


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = str(message.chat.id)

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа к админ-панели.")
        return

    data = load_data()
    students = data["students"]

    if not students:
        bot.send_message(message.chat.id, "База студентов пуста.")
        return

    report = "📋 Список студентов:\n\n"

    for uid, student in students.items():
        name = student.get("name", "Без имени")
        grades = student.get("grades", {})
        debts = student.get("debts", 0)
        risk = calculate_risk(student)

        if grades:
            avg = round(sum(grades.values()) / len(grades), 2)
        else:
            avg = 0.0

        report += f"""👤 {name}
ID: {uid}
📈 Средний балл: {avg}
❗ Долги: {debts} | 🔥 Риск: {risk}%

"""

    bot.send_message(message.chat.id, report)


@bot.message_handler(commands=['status'])
def status(message):
    data = load_data()
    user_id = str(message.chat.id)

    if user_id in data["students"]:
        student = data["students"][user_id]
        name = student["name"]
        grades = student["grades"]
        debts = student["debts"]
        risk = calculate_risk(student)

        grades_text = "\n".join([f"{subj}: {score} баллов" for subj, score in grades.items()])
        text = f"""👤 {name}
📚 Успеваемость:
{grades_text}

❗ Долги: {debts}
🔥 Риск отчисления: {risk}%
"""
    else:
        text = "Ты пока не зарегистрирован в системе.\nНапиши /start, чтобы пройти регистрацию."


    bot.send_message(message.chat.id, text)
 # Показать оценки
@bot.message_handler(commands=['grades'])
def grades(message):
    data = load_data()
    user_id = str(message.chat.id)

    if user_id in data["students"]:
        grades = data["students"][user_id]["grades"]
        text = "\n".join([f"{subject}: {score} баллов" for subject, score in grades.items()])
    else:
        text = "Вы не зарегистрированы в системе."
    
    bot.send_message(message.chat.id, f"📘 Твои оценки:\n{text}")

# Установить баллы по предмету
@bot.message_handler(commands=['add_grade'])
def add_grade(message):
    msg = bot.send_message(message.chat.id, "Введи предмет и баллы через запятую:\nНапример:\nФизика, 70")
    bot.register_next_step_handler(msg, save_grade)

def save_grade(message):
    try:
        subject, score = message.text.split(",")
        subject = subject.strip()
        score = int(score.strip())

        data = load_data()
        user_id = str(message.chat.id)

        if user_id in data["students"]:
            data["students"][user_id]["grades"][subject] = score
            with open("data.json", "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            bot.send_message(message.chat.id, f"✅ Оценка по '{subject}' обновлена: {score} баллов")
        else:
            bot.send_message(message.chat.id, "Вы не зарегистрированы в системе.")
    except:
        bot.send_message(message.chat.id, "Ошибка! Пиши так: Предмет, Баллы")

# Установить количество долгов
@bot.message_handler(commands=['set_debts'])
def set_debts(message):
    msg = bot.send_message(message.chat.id, "Сколько у тебя долгов? Введи число:")
    bot.register_next_step_handler(msg, save_debts)

def save_debts(message):
    try:
        debts = int(message.text.strip())
        data = load_data()
        user_id = str(message.chat.id)

        if user_id in data["students"]:
            data["students"][user_id]["debts"] = debts
            with open("data.json", "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            bot.send_message(message.chat.id, f"❗ Обновлено: теперь у тебя {debts} долгов.")
        else:
            bot.send_message(message.chat.id, "Вы не зарегистрированы в системе.")
    except:
        bot.send_message(message.chat.id, "Ошибка! Введи только число.")
@bot.message_handler(commands=['card'])
def card(message):
    data = load_data()
    user_id = str(message.chat.id)

    if user_id in data["students"]:
        student = data["students"][user_id]
        name = student["name"]
        grades = student["grades"]
        debts = student["debts"]
        risk = calculate_risk(student)

        # Средний балл
        if grades:
            avg = round(sum(grades.values()) / len(grades), 2)
        else:
            avg = 0.0

        grades_text = "\n".join([f"{subj}: {score} баллов" for subj, score in grades.items()]) or "Нет данных"

        text = f"""🎓 Карточка студента

👤 ФИО: {name}
🆔 ID: {user_id}

📚 Успеваемость:
{grades_text}

📈 Средний балл: {avg}
❗ Долгов: {debts}
🔥 Риск отчисления: {risk}%
"""
    else:
        text = "Ты пока не зарегистрирован. Напиши /start, чтобы пройти регистрацию."

    bot.send_message(message.chat.id, text)        
def register_student(message):
    name = message.text.strip()
    user_id = str(message.chat.id)

    new_student = {
        "name": name,
        "grades": {},
        "debts": 0
    }

    data = load_data()
    data["students"][user_id] = new_student

    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    bot.send_message(message.chat.id, f"✅ Добро пожаловать, {name}!\nТеперь ты можешь использовать команды:\n/status — успеваемость\n/add_grade — добавить оценку\n/set_debts — указать долги")

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

bot.polling()
