import os
import sqlite3
from models import create_tables

def init_database():
    """Initialize the database and create necessary directories"""
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Database path
    db_path = os.path.join(data_dir, 'family_planner.db')
    
    # Create database and tables
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    conn.close()
    
    print(f"Database initialized at: {db_path}")
    print("All tables created successfully!")

if __name__ == "__main__":
    init_database() 