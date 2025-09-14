from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from app.models.database import Base, engine, Material
import sqlite3
import os

def add_columns():
    """Add new columns to the materials table if they don't exist"""
    # Get the database path
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "wechat_matrix.db")
    
    # Connect to the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns exist and add them if they don't
        cursor.execute("PRAGMA table_info(materials)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "error_message" not in columns:
            cursor.execute("ALTER TABLE materials ADD COLUMN error_message TEXT")
            
        if "schedule_time" not in columns:
            cursor.execute("ALTER TABLE materials ADD COLUMN schedule_time DATETIME")
            
        if "schedule_status" not in columns:
            cursor.execute("ALTER TABLE materials ADD COLUMN schedule_status TEXT")
            
        conn.commit()
        print("Database updated successfully")
        
    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_columns() 