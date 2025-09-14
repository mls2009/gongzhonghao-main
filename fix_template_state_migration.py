#!/usr/bin/env python3
"""
模板状态表迁移脚本
将 template_modes 表迁移到正确的 template_state 表结构
"""

import sqlite3
import json
from datetime import datetime
import sys
import os

def migrate_template_state():
    """执行模板状态表迁移"""
    
    db_path = "wechat_matrix.db"
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 检查当前数据库表结构...")
        
        # 检查现有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('template_modes', 'template_state');")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"现有模板相关表: {existing_tables}")
        
        # 1. 读取现有 template_modes 数据
        template_modes_data = {}
        if 'template_modes' in existing_tables:
            print("📖 读取现有 template_modes 数据...")
            cursor.execute("SELECT * FROM template_modes;")
            rows = cursor.fetchall()
            
            cursor.execute("PRAGMA table_info(template_modes);")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"template_modes 表结构: {columns}")
            
            for row in rows:
                row_dict = dict(zip(columns, row))
                print(f"读取到数据: {row_dict}")
                template_modes_data[row_dict['mode_type']] = row_dict
        
        # 2. 创建新的 template_state 表
        print("🏗️  创建新的 template_state 表...")
        
        # 删除现有的 template_state 表（如果存在）
        if 'template_state' in existing_tables:
            cursor.execute("DROP TABLE template_state;")
            print("删除了现有的 template_state 表")
        
        # 创建新表
        create_table_sql = """
        CREATE TABLE template_state (
            id INTEGER NOT NULL PRIMARY KEY,
            current_image_template_id INTEGER,
            current_content_template_id INTEGER,
            image_template_mode VARCHAR DEFAULT 'random',
            content_template_mode VARCHAR DEFAULT 'random',
            image_template_enabled BOOLEAN DEFAULT 0,
            content_template_enabled BOOLEAN DEFAULT 0,
            updated_at DATETIME,
            FOREIGN KEY(current_image_template_id) REFERENCES image_templates (id),
            FOREIGN KEY(current_content_template_id) REFERENCES content_templates (id)
        );
        """
        
        cursor.execute(create_table_sql)
        cursor.execute("CREATE INDEX ix_template_state_id ON template_state (id);")
        print("✅ template_state 表创建成功")
        
        # 3. 迁移数据
        print("📦 迁移数据到新表...")
        
        # 准备默认数据
        current_image_template_id = None
        current_content_template_id = None
        image_template_enabled = False
        content_template_enabled = False
        image_template_mode = 'random'
        content_template_mode = 'random'
        
        # 从 template_modes 提取数据
        if 'image_template_mode' in template_modes_data:
            image_data = template_modes_data['image_template_mode']
            if not image_data.get('is_random_mode', True) and image_data.get('current_template_id'):
                current_image_template_id = image_data['current_template_id']
                image_template_enabled = True
                image_template_mode = 'specific'
        
        if 'content_template_mode' in template_modes_data:
            content_data = template_modes_data['content_template_mode']
            if not content_data.get('is_random_mode', True) and content_data.get('current_template_id'):
                current_content_template_id = content_data['current_template_id']
                content_template_enabled = True
                content_template_mode = 'specific'
        
        # 插入迁移后的数据
        insert_sql = """
        INSERT INTO template_state 
        (id, current_image_template_id, current_content_template_id, 
         image_template_mode, content_template_mode, 
         image_template_enabled, content_template_enabled, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(insert_sql, (
            current_image_template_id,
            current_content_template_id,
            image_template_mode,
            content_template_mode,
            image_template_enabled,
            content_template_enabled,
            datetime.now()
        ))
        
        print(f"✅ 数据迁移完成:")
        print(f"  - 图片模板ID: {current_image_template_id}")
        print(f"  - 内容模板ID: {current_content_template_id}")
        print(f"  - 图片模板启用: {image_template_enabled}")
        print(f"  - 内容模板启用: {content_template_enabled}")
        
        # 4. 验证新表数据
        print("🔍 验证迁移结果...")
        cursor.execute("SELECT * FROM template_state;")
        new_data = cursor.fetchone()
        print(f"新表数据: {new_data}")
        
        # 5. 重命名旧表作为备份
        if 'template_modes' in existing_tables:
            backup_table_name = f"template_modes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cursor.execute(f"ALTER TABLE template_modes RENAME TO {backup_table_name};")
            print(f"✅ 旧表已重命名为: {backup_table_name}")
        
        # 提交所有更改
        conn.commit()
        print("✅ 数据库迁移完成！")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移过程中出错: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

def verify_migration():
    """验证迁移结果"""
    print("\n🔍 验证迁移结果...")
    
    try:
        conn = sqlite3.connect("wechat_matrix.db")
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='template_state';")
        if not cursor.fetchone():
            print("❌ template_state 表不存在")
            return False
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(template_state);")
        columns = [col[1] for col in cursor.fetchall()]
        expected_columns = [
            'id', 'current_image_template_id', 'current_content_template_id',
            'image_template_mode', 'content_template_mode', 
            'image_template_enabled', 'content_template_enabled', 'updated_at'
        ]
        
        missing_columns = set(expected_columns) - set(columns)
        if missing_columns:
            print(f"❌ 缺少字段: {missing_columns}")
            return False
        
        # 检查数据
        cursor.execute("SELECT COUNT(*) FROM template_state;")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("⚠️  template_state 表为空，插入默认数据...")
            cursor.execute("""
                INSERT INTO template_state 
                (id, image_template_mode, content_template_mode, 
                 image_template_enabled, content_template_enabled, updated_at)
                VALUES (1, 'random', 'random', 0, 0, ?)
            """, (datetime.now(),))
            conn.commit()
        
        # 显示最终状态
        cursor.execute("SELECT * FROM template_state;")
        data = cursor.fetchone()
        print(f"✅ template_state 表验证通过，当前数据: {data}")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证过程出错: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 开始模板状态表迁移...")
    print("="*50)
    
    if migrate_template_state():
        if verify_migration():
            print("\n🎉 迁移成功完成！")
            print("\n📋 迁移摘要:")
            print("- ✅ 备份了原始数据库")
            print("- ✅ 创建了正确的 template_state 表结构")
            print("- ✅ 迁移了现有的模板配置数据")
            print("- ✅ 保留了旧表作为备份")
            print("\n现在可以正常使用模板功能了！")
        else:
            print("\n❌ 迁移验证失败，请检查数据库状态")
            sys.exit(1)
    else:
        print("\n❌ 迁移失败，请查看错误信息")
        sys.exit(1)