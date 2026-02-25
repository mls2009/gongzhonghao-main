import sys
import os

# Add 'app' directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from models.database import get_db, XiaohongshuSettings, engine
from sqlalchemy.orm import Session

def verify_settings():
    db = next(get_db())
    try:
        settings = db.query(XiaohongshuSettings).first()
        if not settings:
            print("No settings found!")
            # Create one
            settings = XiaohongshuSettings(materials_path="/tmp")
            db.add(settings)
            db.commit()
            print("Created default settings.")
        
        print(f"Current add_product_enabled: {settings.add_product_enabled}")
        
        # Simulate toggle ON
        settings.add_product_enabled = True
        db.commit()
        print("Toggled ON. Committed.")
        
        # Re-read
        db.expire_all()
        s2 = db.query(XiaohongshuSettings).first()
        print(f"Read after toggle ON: {s2.add_product_enabled}")
        
        # Simulate toggle OFF
        settings.add_product_enabled = False
        db.commit()
        print("Toggled OFF. Committed.")
        
        # Re-read
        db.expire_all()
        s3 = db.query(XiaohongshuSettings).first()
        print(f"Read after toggle OFF: {s3.add_product_enabled}")
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_settings()
