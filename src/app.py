import os


class Application:
    def __init__(self, db_manager, formatter):
        self.db = db_manager
        self.formatter = formatter

    def save_results(self, formatted_data, format_type):
        os.makedirs('results', exist_ok=True)
        filename = f"results/results.{format_type}"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(formatted_data)
        print(f"Results saved to: {filename}")

    def run(self, rooms_file, students_file, format_type):
        self.db.create_tables()
        self.db.load_rooms(rooms_file)
        self.db.load_students(students_file)
        self.db.create_indexes()

        results = self.db.execute_queries()
        results['indexes_sql'] = self.db.get_indexes_sql()


        formatted_result = self.formatter.format(results)

        self.save_results(formatted_result, format_type)

        self.db.close()
        print('Done!')

