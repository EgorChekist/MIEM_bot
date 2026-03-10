import sqlite3


class Database:
    def __init__(self, db_file):
        self.db_file = db_file

    def _execute(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        """Вспомогательный метод для выполнения запросов."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if commit:
                conn.commit()

            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            return cursor

    def create_tables(self):
        """Создание таблиц по твоему шаблону."""
        users_query = """
        CREATE TABLE IF NOT EXISTS "users" (
            "id" INTEGER NOT NULL UNIQUE,
            "user_id" INTEGER NOT NULL UNIQUE,
            "username" TEXT NOT NULL,
            "status" TEXT NOT NULL,
            PRIMARY KEY("id" AUTOINCREMENT)
        );
        """
        categories_query = """
        CREATE TABLE IF NOT EXISTS "categories" (
            "student_id" INTEGER NOT NULL,
            "category" TEXT NOT NULL,
            FOREIGN KEY("student_id") REFERENCES "users"("id")
        );
        """
        self._execute(users_query, commit=True)
        self._execute(categories_query, commit=True)

    # --- Методы для работы с Users ---

    def add_user(self, user_id, username, status):
        query = "INSERT INTO users (user_id, username, status) VALUES (?, ?, ?)"
        return self._execute(query, (user_id, username, status), commit=True)

    def get_user(self, user_id):
        query = "SELECT * FROM users WHERE user_id = ?"
        return self._execute(query, (user_id,), fetchone=True)


    def add_category(self, student_internal_id, category_name):
        """Добавление категории (используется внутренний id из таблицы users)."""
        query = "INSERT INTO categories (student_id, category) VALUES (?, ?)"
        return self._execute(query, (student_internal_id, category_name), commit=True)

    def get_user_categories(self, student_internal_id):
        query = "SELECT category FROM categories WHERE student_id = ?"
        return self._execute(query, (student_internal_id,), fetchall=True)


# Пример использования:
if __name__ == "__main__":
    db = Database("database.db")
    db.create_tables()

    # Добавляем пользователя
    try:
        db.add_user(916465455, "haru", "admin")
    except sqlite3.IntegrityError:
        print("Пользователь уже существует")

    # Получаем ID пользователя из базы и добавляем ему категорию
    user = db.get_user(916465455)
    print(user)
