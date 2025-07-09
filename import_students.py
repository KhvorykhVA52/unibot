import sqlite3
import json

students_list = [
    "Арапов Тимофей Яковлевич",
    "Березовская Галина Олеговна",
    "Галимова Алина Салаватовна",
    "Донской Иван Андреевич",
    "Каранда Александр Романович",
    "Комарова Маргарита Васильевна",
    "Конева Дарья Денисовна",
    "Коржук Артур Петрович",
    "Королев Егор Сергеевич",
    "Лавринович Елизавета Дмитриевна",
    "Манякин Никита Андреевич",
    "Медяничев Денис Игоревич",
    "Мироненко Сергей Эдуардович",
    "Морозов Сергей Максимович",
    "Мохноногова Полина Викторовна",
    "Рауш Кирилл Николаевич",
    "Сафонов Руслан Васильевич",
    "Соначев Андрей Вячеславович",
    "Соснин Федор Михайлович",
    "Сычев Александр Дмитриевич",
    "Тясин Илья Александрович",
    "Ухалов Арсений Константинович",
    "Федорова Дарья Артемовна",
    "Хворых Виктор Александрович",
    "Шамагулова Ангелина Рушановна"
]

faculty = "ВШЦТ"
specialty = "Автоматизированные системы обработки информации и управления"
group = "АСОиУБ-24-1"

conn = sqlite3.connect("students.db")
cursor = conn.cursor()

# 🛠 Создаём таблицу, если её нет
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    faculty TEXT NOT NULL,
    specialty TEXT NOT NULL,
    group_name TEXT NOT NULL,
    grades TEXT,
    debts INTEGER
)
""")

# 🔁 Вставляем студентов
for name in students_list:
    cursor.execute("""
        INSERT INTO students (id, name, faculty, specialty, group_name, grades, debts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (None, name, faculty, specialty, group, json.dumps({}), 0))

conn.commit()
conn.close()

print("✅ Таблица создана, студенты добавлены в базу.")
