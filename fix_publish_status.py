#!/usr/bin/env python3
"""
修复发布状态的脚本
用于处理发布日志显示成功但数据库状态未正确更新的问题
"""

import sqlite3
import sys
from datetime import datetime

def fix_publish_status(material_id: int):
    """修复指定素材的发布状态"""
    conn = sqlite3.connect('app/wechat_matrix.db')
    cursor = conn.cursor()
    
    try:
        # 获取素材信息
        cursor.execute('SELECT id, title, status, publish_status, account_id FROM materials WHERE id = ?', (material_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"错误: 找不到ID为 {material_id} 的素材")
            return False
            
        material_id, title, status, publish_status, account_id = result
        print(f"当前素材状态: ID={material_id}, 标题={title}, 状态={status}, 发布状态={publish_status}")
        
        # 如果账号ID为空，尝试分配一个默认账号
        if not account_id:
            cursor.execute('SELECT id, username FROM accounts WHERE account_type = "公众号" LIMIT 1')
            account_result = cursor.fetchone()
            if account_result:
                account_id = account_result[0]
                cursor.execute('UPDATE materials SET account_id = ? WHERE id = ?', (account_id, material_id))
                print(f"已分配账号ID: {account_id} ({account_result[1]})")
            else:
                print("警告: 没有找到可用的公众号账号")
        
        # 更新为发布成功状态
        cursor.execute('''
            UPDATE materials 
            SET status = 'published', 
                publish_status = 'success', 
                publish_time = ? 
            WHERE id = ?
        ''', (datetime.now().isoformat(), material_id))
        
        conn.commit()
        print(f"✅ 素材 {material_id} 已更新为发布成功状态")
        return True
        
    except Exception as e:
        print(f"错误: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def list_problem_materials():
    """列出可能存在问题的素材"""
    conn = sqlite3.connect('app/wechat_matrix.db')
    cursor = conn.cursor()
    
    try:
        # 查找状态为unpublished但可能已发布的素材
        cursor.execute('''
            SELECT id, title, status, publish_status, account_id 
            FROM materials 
            WHERE status = 'unpublished' OR publish_status IS NULL
            ORDER BY id DESC
        ''')
        results = cursor.fetchall()
        
        if results:
            print("可能存在问题的素材:")
            print("ID\t标题\t\t\t状态\t发布状态\t账号ID")
            print("-" * 80)
            for row in results:
                title = row[1][:20] + "..." if len(row[1]) > 20 else row[1]
                print(f"{row[0]}\t{title:<20}\t{row[2]}\t{row[3]}\t\t{row[4]}")
        else:
            print("没有找到问题素材")
            
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 fix_publish_status.py list              # 列出问题素材")
        print("  python3 fix_publish_status.py fix <材料ID>      # 修复指定素材")
        print("  python3 fix_publish_status.py fix 1             # 修复素材ID 1")
    elif sys.argv[1] == "list":
        list_problem_materials()
    elif sys.argv[1] == "fix" and len(sys.argv) > 2:
        try:
            material_id = int(sys.argv[2])
            fix_publish_status(material_id)
        except ValueError:
            print("错误: 素材ID必须是数字")
    else:
        print("无效的命令")