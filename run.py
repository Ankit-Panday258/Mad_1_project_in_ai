import os
from app import create_app
from app.models import db
from seed_data import init_and_seed_database

app = create_app()

if __name__ == '__main__':
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'examination_portal.db')
    if not os.path.exists(db_path):
        print("Database not found. Programmatically initializing and seeding database...")
        init_and_seed_database()

    print("\n" + "="*60)
    print("Examination Management Portal (EMP) Starting...")
    print("Open http://127.0.0.1:5000 in your web browser.")
    print("="*60 + "\n")
    app.run(host='127.0.0.1', port=5000, debug=True)
