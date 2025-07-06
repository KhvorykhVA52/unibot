import sqlite3
import json

DB_NAME = "students.db"

# Создание таблицы, если не существует
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        name TEXT,
        faculty TEXT,
        specialty TEXT,
        group_name TEXT,
        grades TEXT,
        debts INTEGER
    )
    ''')

    conn.commit()
    conn.close()

# Добавление нового студента
def add_student(user_id, name, faculty, specialty, group_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO students (id, name, faculty, specialty, group_name, grades, debts)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, faculty, specialty, group_name, json.dumps({}), 0))

    conn.commit()
    conn.close()

# Проверка, зарегистрирован ли студент
def student_exists(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM students WHERE id = ?', (user_id,))
    result = cursor.fetchone()

    conn.close()
    return result is not None

# Получить данные студента
def get_student(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM students WHERE id = ?', (user_id,))
    row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "faculty": row[2],
            "specialty": row[3],
            "group": row[4],
            "grades": json.loads(row[5]) if row[5] else {},
            "debts": row[6]
        }
    else:
        return None

# Обновить оценки
def update_grades(user_id, grades_dict):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    grades_json = json.dumps(grades_dict)

    cursor.execute('''
    UPDATE students SET grades = ? WHERE id = ?
    ''', (grades_json, user_id))

    conn.commit()
    conn.close()

# Обновить количество долгов
def update_debts(user_id, debts):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
    UPDATE students SET debts = ? WHERE id = ?
    ''', (debts, user_id))

    conn.commit()
    conn.close()

def get_all_students():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()
    conn.close()

    students = []
    for row in rows:
        student = {
            "id": row[0],
            "name": row[1],
            "faculty": row[2],
            "specialty": row[3],
            "group": row[4],
            "grades": json.loads(row[5]),
            "debts": row[6]
        }
        students.append(student)
    return students
