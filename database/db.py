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
            "gender" VARCHAR(2) NOT NULL,
            "degree" VARCHAR(30) NOT NULL,
            "year" INTEGER NOT NULL,
            "program" VARCHAR(160) NOT NULL,
            "group" VARCHAR(20) NOT NULL,
            "category" VARCHAR(10) NOT NULL,
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

    def add_category(self, student_internal_id, student_gender, student_degree, student_year, student_program,
                     student_group,
                     student_category):
        """Добавление категории (используется внутренний id из таблицы users)."""
        query = """INSERT INTO categories ("student_id", "gender","degree", "year", "program", "group", "category") VALUES (?, ?, ?, ?, ?, ?, ?)"""
        return self._execute(query, (
            student_internal_id, student_gender, student_degree, student_year, student_program, student_group,
            student_category),
                             commit=True)

    def get_filtered_users(self, filters, mode="AND"):
        """
        filters: dict типа {'year': ['1', '2'], 'program': ['ИВТ']}
        mode: "AND" или "OR"
        """
        if not filters:
            return []

        query = """
            SELECT DISTINCT u.user_id 
            FROM users u 
            JOIN categories c ON u.id = c.student_id 
            WHERE 
        """

        conditions = []
        params = []

        for column, values in filters.items():
            if values:
                # Создаем строку вида: column IN (?, ?, ?)
                placeholders = ", ".join(["?"] * len(values))
                conditions.append(f"c.{column} IN ({placeholders})")
                params.extend(values)

        # Соединяем категории через выбранный режим (AND или OR)
        query += f" {mode} ".join(conditions)

        # Выполняем запрос
        return self._execute(query, params, fetchall=True)

    def get_user_categories(self, student_internal_id):
        query = "SELECT category FROM categories WHERE student_id = ?"
        return self._execute(query, (student_internal_id,), fetchall=True)

    def query(self, query):
        query = query
        return self._execute(query)


# Пример использования:
if __name__ == "__main__":
    db = Database("database.db")
    db.create_tables()

    # Добавляем пользователя
    try:
        db.add_user(916465455, "haru", "admin")
        db.add_user(1001, "ivan", "student")
        db.add_user(1002, "dima", "student")
        db.add_user(1003, "botya", "student")
        db.add_user(1004, "Gazan", "student")
    except sqlite3.IntegrityError:
        print("Пользователь уже существует123")

    try:
        db.add_category(1, "M", "Бакалавриат", "2", "ИВТ", "БИВ246", "Бюджет")
        db.add_category(2, "Ж", "Магистратура", "3", "ПМ", "БПМ242", "Платник")
        db.add_category(3, "Ж", "Бакалавриат", "4", "ПИ", "БПИ231", "Платник")
        db.add_category(4, "M", "Специалитет", "5", "ИБ", "БИБ222", "Платник")
        db.add_category(5, "M", "Бакалавриат", "1", "ИВТ", "БИВ246", "Платник")
    except sqlite3.IntegrityError:
        print("Пользователь уже существует")

    user = db.get_user(916465455)
    print(user)
