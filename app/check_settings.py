from app.models.database import get_db, Settings, Material
from datetime import datetime

def check_settings():
    db = next(get_db())
    
    # 获取设置信息
    settings = db.query(Settings).first()
    print(f"素材库路径: {settings.materials_path}")
    print(f"最后扫描时间: {settings.last_scan}")
    print("\n数据库统计:")
    
    # 获取素材统计
    total_materials = db.query(Material).count()
    published_materials = db.query(Material).filter(Material.status == "published").count()
    unpublished_materials = db.query(Material).filter(Material.status == "unpublished").count()
    scheduled_materials = db.query(Material).filter(
        Material.status == "unpublished",
        Material.schedule_time != None
    ).count()
    
    print(f"总素材数: {total_materials}")
    print(f"已发布素材数: {published_materials}")
    print(f"未发布素材数: {unpublished_materials}")
    print(f"预约发布素材数: {scheduled_materials}")
    
    # 显示最近的预约发布任务
    print("\n最近的预约发布任务:")
    scheduled_tasks = db.query(Material).filter(
        Material.status == "unpublished",
        Material.schedule_time != None
    ).order_by(Material.schedule_time.asc()).limit(5).all()
    
    for task in scheduled_tasks:
        print(f"标题: {task.title}")
        print(f"预约时间: {task.schedule_time}")
        print("---")

if __name__ == "__main__":
    check_settings() 