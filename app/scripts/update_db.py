from sqlalchemy import create_engine, text
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SQLALCHEMY_DATABASE_URL, engine

def update_database():
    try:
        # 添加 content 列到 materials 表
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE materials ADD COLUMN content TEXT;"))
            conn.commit()
            print("成功添加 content 列到 materials 表")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("content 列已存在")
        else:
            print(f"更新数据库时出错: {str(e)}")

if __name__ == "__main__":
    update_database() 