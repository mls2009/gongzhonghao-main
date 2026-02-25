import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'app'))

from models.database import get_db, XiaohongshuSettings

def check_duplicate_settings():
    db = next(get_db())
    try:
        count = db.query(XiaohongshuSettings).count()
        print(f"Total XiaohongshuSettings rows: {count}")
        
        all_settings = db.query(XiaohongshuSettings).all()
        for idx, s in enumerate(all_settings):
            print(f"Row {idx+1}: ID={s.id}, AddProduct={s.add_product_enabled}, AutoPublish={s.auto_publish_enabled}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_duplicate_settings()
