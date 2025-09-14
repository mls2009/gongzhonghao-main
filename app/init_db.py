from app.models.database import Base, engine, get_db, Account, Material, Settings
from datetime import datetime

def init_database():
    """初始化数据库"""
    # 删除所有现有表并重新创建
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 创建示例账号
        accounts = [
            Account(
                username="example_wechat",
                password="password123",
                browser_id="browser123",
                account_type="公众号",
                author_name="示例公众号",
                status="active"
            ),
            Account(
                username="example_toutiao",
                password="password123",
                browser_id="browser456",
                account_type="头条号",
                author_name="示例头条号",
                status="active"
            )
        ]
        db.add_all(accounts)
        
        # 创建示例素材
        materials = [
            Material(
                title="人工智能发展趋势",
                original_title="AI_Development_Trends",
                word_count=2000,
                image_count=5,
                status="unpublished"
            ),
            Material(
                title="Web3.0技术解析",
                original_title="Web3_Tech_Analysis",
                word_count=1800,
                image_count=3,
                status="unpublished"
            ),
            Material(
                title="元宇宙发展前景",
                original_title="Metaverse_Future",
                word_count=2200,
                image_count=6,
                status="unpublished"
            )
        ]
        db.add_all(materials)
        
        # 创建默认设置
        settings = Settings(
            materials_path="C:/materials"  # 默认素材库路径
        )
        db.add(settings)
        
        db.commit()
        print("数据库初始化完成")
        
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def update_database():
    """更新数据库结构"""
    # 这将保留现有数据，只更新表结构
    Base.metadata.create_all(bind=engine)
    print("数据库结构已更新")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        update_database()
    else:
        init_database() 