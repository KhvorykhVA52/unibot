import sqlite3
import json
import time

DB_NAME = "students.db"

def connect_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# Инициализация базы
def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT,
            faculty TEXT,
            specialty TEXT,
            group_name TEXT,
            grades TEXT,
            debts INTEGER,
            last_grades TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            user_id TEXT,
            title TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Добавление нового студента
def add_student(user_id, name, faculty, specialty, group_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO students (id, name, faculty, specialty, group_name, grades, debts, last_grades)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, faculty, specialty, group_name, json.dumps({}), 0, json.dumps({})))
    conn.commit()
    conn.close()

# Проверка регистрации
def student_exists(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM students WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Получение данных студента
def get_student(user_id):
    conn = connect_db()
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
            "debts": row[6],
            "last_grades": json.loads(row[7]) if row[7] else {}
        }
    return None

# Обновление оценок (с защитой от блокировки)
def update_grades(user_id, grades):
    for i in range(5):
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute('SELECT grades FROM students WHERE id = ?', (user_id,))
            old = cursor.fetchone()
            old_grades = json.loads(old[0]) if old and old[0] else {}

            cursor.execute('UPDATE students SET grades = ? WHERE id = ?', (json.dumps(grades), user_id))
            conn.commit()

            # если это первая оценка, добавляем ачивку "Первые шаги"
            if len(old_grades) == 0 and len(grades) > 0:
                add_achievement(user_id, "🎯 Первые шаги")

            conn.close()
            return
        except sqlite3.OperationalError:
            print(f"[LOCKED] Попытка {i+1} — база занята, retry...")
            time.sleep(0.5)

# Обновление last_grades
def update_last_grades(user_id, grades):
    for i in range(5):
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE students SET last_grades = ? WHERE id = ?', (json.dumps(grades), user_id))
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError:
            print(f"[LOCKED] update_last_grades попытка {i+1} — база занята.")
            time.sleep(0.5)

# Обновление долгов
def update_debts(user_id, debts):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE students SET debts = ? WHERE id = ?', (debts, user_id))
    conn.commit()
    conn.close()

# Студенты без Telegram ID
def get_students_by_group(faculty, specialty, group_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name FROM students
        WHERE faculty=? AND specialty=? AND group_name=? AND id IS NULL
    ''', (faculty, specialty, group_name))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# Привязка Telegram ID по ФИО
def assign_user_id_to_student(user_id, name, faculty, specialty, group_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE students SET id = ?
        WHERE name=? AND faculty=? AND specialty=? AND group_name=? AND id IS NULL
    ''', (user_id, name, faculty, specialty, group_name))
    conn.commit()
    conn.close()

# Получение всех студентов
def get_all_students():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, faculty, specialty, group_name, grades, debts, last_grades FROM students')
    rows = cursor.fetchall()
    conn.close()
    students = []
    for row in rows:
        students.append({
            "id": row[0],
            "name": row[1],
            "faculty": row[2],
            "specialty": row[3],
            "group": row[4],
            "grades": json.loads(row[5] or "{}"),
            "debts": row[6],
            "last_grades": json.loads(row[7] or "{}")
        })
    return students

# Добавить достижение
def add_achievement(user_id, title):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM achievements WHERE user_id=? AND title=?', (user_id, title))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute('INSERT INTO achievements (user_id, title) VALUES (?, ?)', (user_id, title))
        conn.commit()
    conn.close()

# Получить список достижений
def get_achievements(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT title FROM achievements WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
