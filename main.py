
import argparse
from src.config import DB_CONFIG, STUDENTS_FILE, ROOMS_FILE
from src.db_manager import DatabaseManager
from src.formatters import JSONFormatter, XMLFormatter
from src.app import Application


def main():
    parser = argparse.ArgumentParser(
        description='Load student and room data into PostgreSQL'
    )
    parser.add_argument(
        '--students',
        required=False,
        default=STUDENTS_FILE,
        help='Path to students.json file'
    )
    parser.add_argument(
        '--rooms',
        required=False,
        default=ROOMS_FILE,
        help='Path to rooms.json file'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'xml'],
        default='json',
        help='Output format (json or xml)'
    )
    args = parser.parse_args()

    if args.format == 'json':
        formatter = JSONFormatter()
    else:
        formatter = XMLFormatter()

    db = DatabaseManager(DB_CONFIG)

    app = Application(db, formatter)
    app.run(args.rooms, args.students, args.format)


if __name__ == '__main__':
    main()