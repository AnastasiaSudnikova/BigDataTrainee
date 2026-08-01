import psycopg2
import json


class DatabaseManager:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()
        print("Connected to database")

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                birthday DATE NOT NULL,
                sex CHAR(1) CHECK (sex IN ('M', 'F')),
                room_id INTEGER REFERENCES rooms(id) ON DELETE CASCADE
            );
        """)
        self.conn.commit()
        print("Tables created")

    def load_rooms(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            rooms = json.load(f)

        batch_size = 1000
        all_rooms_data = [(room['id'], room['name']) for room in rooms]

        total_loaded = 0
        for i in range(0, len(all_rooms_data), batch_size):
            batch = all_rooms_data[i:i + batch_size]
            self.cursor.executemany(
                "INSERT INTO rooms (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
                batch
            )
            self.conn.commit()
            total_loaded += len(batch)
            print(f"Loaded rooms {total_loaded}")

        print(f"Loaded {total_loaded} rooms total")

    def load_students(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            students = json.load(f)

        batch_size = 1000

        all_students_data = []
        for student in students:
            birthday = student['birthday'].split('T')[0]
            all_students_data.append(
                (student['id'], student['name'], birthday, student['sex'], student['room'])
            )

        total_loaded = 0
        for i in range(0, len(all_students_data), batch_size):
            batch = all_students_data[i:i + batch_size]
            self.cursor.executemany(
                """INSERT INTO students (id, name, birthday, sex, room_id) 
                   VALUES (%s, %s, %s, %s, %s) 
                   ON CONFLICT (id) DO NOTHING;""",
                batch
            )
            self.conn.commit()
            total_loaded += len(batch)
            print(f"Loaded  students {total_loaded}")

        print(f"Loaded {total_loaded} students total")

    def create_indexes(self):
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_students_room_id ON students(room_id);",
            "CREATE INDEX IF NOT EXISTS idx_students_birthday ON students(birthday);",
            "CREATE INDEX IF NOT EXISTS idx_rooms_id ON rooms(id);"
        ]
        for sql in indexes:
            self.cursor.execute(sql)
        self.conn.commit()
        print("Indexes created")

    def get_indexes_sql(self):
        return """
-- INDEXES FOR QUERY OPTIMIZATION
CREATE INDEX IF NOT EXISTS idx_students_room_id ON students(room_id);
CREATE INDEX IF NOT EXISTS idx_students_birthday ON students(birthday);
CREATE INDEX IF NOT EXISTS idx_students_sex ON students(sex);
CREATE INDEX IF NOT EXISTS idx_rooms_id ON rooms(id);
"""

    def execute_queries(self):
        results = {}

        self.cursor.execute("""
            SELECT r.id, r.name, COUNT(s.id) as student_count
            FROM rooms r
            LEFT JOIN students s ON r.id = s.room_id
            GROUP BY r.id, r.name
            ORDER BY r.id;
        """)
        results['rooms_with_students'] = [
            {'id': row[0], 'name': row[1], 'student_count': row[2]}
            for row in self.cursor.fetchall()
        ]


        self.cursor.execute("""
            SELECT r.id, r.name, 
                   ROUND(AVG(EXTRACT(YEAR FROM AGE(s.birthday))), 2) as avg_age
            FROM rooms r
            JOIN students s ON r.id = s.room_id
            GROUP BY r.id, r.name
            HAVING COUNT(s.id) > 0
            ORDER BY avg_age ASC
            LIMIT 5;
        """)
        results['rooms_smallest_avg_age'] = [
            {'id': row[0], 'name': row[1], 'avg_age': row[2]}
            for row in self.cursor.fetchall()
        ]


        self.cursor.execute("""
            SELECT r.id, r.name, 
                   ROUND(MAX(EXTRACT(YEAR FROM AGE(s.birthday))) - 
                         MIN(EXTRACT(YEAR FROM AGE(s.birthday))), 2) as age_diff
            FROM rooms r
            JOIN students s ON r.id = s.room_id
            GROUP BY r.id, r.name
            HAVING COUNT(s.id) > 1
            ORDER BY age_diff DESC
            LIMIT 5;
        """)
        results['rooms_max_age_diff'] = [
            {'id': row[0], 'name': row[1], 'age_diff': row[2]}
            for row in self.cursor.fetchall()
        ]


        self.cursor.execute("""
            SELECT DISTINCT r.id, r.name
            FROM rooms r
            JOIN students s ON r.id = s.room_id
            GROUP BY r.id, r.name
            HAVING COUNT(DISTINCT s.sex) > 1;
        """)
        results['rooms_mixed_gender'] = [
            {'id': row[0], 'name': row[1]}
            for row in self.cursor.fetchall()
        ]

        return results

    def close(self):
        self.cursor.close()
        self.conn.close()
        print("Database connection closed")