import json
from database import init_db, add_student

# Инициализация базы (на всякий случай)
init_db()

# Путь к файлу JSON
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for user_id, info in data["students"].items():
    name = info.get("name", "Неизвестный")
    grades = info.get("grades", {})
    debts = info.get("debts", 0)

    # Временные значения для факультета, специальности и группы
    faculty = "Не указан"
    specialty = "Не указана"
    group = "Не указана"

    print(f"📥 Импортируем: {name} | ID: {user_id}")

    add_student(
        user_id=user_id,
        name=name,
        faculty=faculty,
        specialty=specialty,
        group_name=group
    )

    # Обновление оценок и долгов (если хочешь — добавим сюда)
    from database import update_grades, update_debts
    update_grades(user_id, grades)
    update_debts(user_id, debts)

print("\n✅ Импорт завершён.")
ё