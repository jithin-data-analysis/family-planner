import os
import sqlite3
from models import create_tables

def init_database():
    """Initialize the database and create necessary tables"""
    try:
        # Try to use the data directory in the project root
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    except:
        # If that fails, use the current directory
        data_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Use absolute path for database file
    db_path = os.path.join(data_dir, 'family_planner.db')
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    # Create tables
    create_tables(conn)
    
    # Close connection
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database() 