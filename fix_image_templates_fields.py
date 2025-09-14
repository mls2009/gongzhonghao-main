#!/usr/bin/env python3
"""
修复 image_templates 表字段缺失问题
添加缺失的 text_color 字段
"""

import sqlite3
from datetime import datetime
import os

def fix_image_templates_fields():
    """修复 image_templates 表字段"""
    
    db_path = "wechat_matrix.db"
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 检查 image_templates 表结构...")
        
        # 检查当前字段
        cursor.execute("PRAGMA table_info(image_templates);")
        current_fields = {col[1]: col[2] for col in cursor.fetchall()}
        print(f"当前字段: {list(current_fields.keys())}")
        
        # 需要的字段和默认值
        required_fields = {
            'text_color': ('VARCHAR', '#2c3e50'),
            'created_at': ('DATETIME', None),
            'updated_at': ('DATETIME', None)
        }
        
        # 添加缺失字段
        fields_added = []
        for field_name, (field_type, default_value) in required_fields.items():
            if field_name not in current_fields:
                try:
                    if default_value:
                        alter_sql = f"ALTER TABLE image_templates ADD COLUMN {field_name} {field_type} DEFAULT '{default_value}'"
                    else:
                        alter_sql = f"ALTER TABLE image_templates ADD COLUMN {field_name} {field_type}"
                    
                    cursor.execute(alter_sql)
                    fields_added.append(field_name)
                    print(f"✅ 添加字段: {field_name}")
                except Exception as e:
                    print(f"⚠️  添加字段 {field_name} 时出错: {e}")
        
        # 更新现有记录的时间戳
        if 'created_at' in fields_added or 'updated_at' in fields_added:
            current_time = datetime.now().isoformat()
            cursor.execute("""
                UPDATE image_templates 
                SET created_at = COALESCE(created_at, ?),
                    updated_at = COALESCE(updated_at, ?)
                WHERE created_at IS NULL OR updated_at IS NULL
            """, (current_time, current_time))
            print("✅ 更新了现有记录的时间戳")
        
        # 验证更新后的字段
        cursor.execute("PRAGMA table_info(image_templates);")
        updated_fields = [col[1] for col in cursor.fetchall()]
        print(f"更新后字段: {updated_fields}")
        
        # 检查数据
        cursor.execute("SELECT * FROM image_templates;")
        templates = cursor.fetchall()
        print(f"✅ 当前有 {len(templates)} 个图片模板")
        
        if templates:
            cursor.execute("PRAGMA table_info(image_templates);")
            columns = [col[1] for col in cursor.fetchall()]
            for i, template in enumerate(templates):
                template_dict = dict(zip(columns, template))
                print(f"模板 {i+1}: {template_dict}")
        
        conn.commit()
        print("✅ image_templates 表字段修复完成！")
        
        return True
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 开始修复 image_templates 表字段...")
    print("="*50)
    
    if fix_image_templates_fields():
        print("\n🎉 字段修复成功完成！")
    else:
        print("\n❌ 字段修复失败")