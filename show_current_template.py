#!/usr/bin/env python3
"""
显示当前正在使用的模板信息
"""

import sys
import os
import sqlite3
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def show_current_template_status():
    """显示当前模板状态"""
    try:
        conn = sqlite3.connect("app/wechat_matrix.db")
        cursor = conn.cursor()
        
        print("🎯 当前模板使用情况:")
        print("="*50)
        
        # 获取当前模板状态
        cursor.execute("""
            SELECT current_image_template_id, image_template_enabled, 
                   image_template_mode, updated_at 
            FROM template_state WHERE id = 1
        """)
        state = cursor.fetchone()
        
        if not state:
            print("❌ 没有找到模板状态")
            return
            
        template_id, enabled, mode, updated = state
        print(f"📊 模板状态:")
        print(f"   - 启用状态: {'✅ 启用' if enabled else '❌ 未启用'}")
        print(f"   - 当前模板ID: {template_id}")
        print(f"   - 模板模式: {mode}")
        print(f"   - 最后更新: {updated}")
        
        if not enabled or not template_id:
            print("⚠️  当前使用随机模式")
            return
            
        # 获取具体模板信息
        cursor.execute("""
            SELECT id, name, template_type, text_style, background_style, 
                   font_size, text_color, line_height, mask_opacity
            FROM image_templates WHERE id = ?
        """, (template_id,))
        template = cursor.fetchone()
        
        if template:
            tid, name, ttype, style, bg, size, color, height, opacity = template
            print(f"\n🎨 当前使用的模板详情:")
            print(f"   - ID: {tid}")
            print(f"   - 名称: '{name}'")
            print(f"   - 类型: {ttype} ({'插入模式' if ttype == 'insert' else '覆盖模式'})")
            print(f"   - 文字样式: {style}")
            print(f"   - 背景样式: {bg}")
            print(f"   - 字体大小: {size}")
            print(f"   - 文字颜色: {color}")
            print(f"   - 行高: {height}")
            print(f"   - 蒙版透明度: {opacity}")
            
            print(f"\n🔍 这意味着:")
            print(f"   当你发布素材时，将会使用 '{name}' 模板")
            if ttype == 'insert':
                print(f"   系统会创建新的图片并插入到素材文件夹的第一位")
            else:
                print(f"   系统会在第一张图片上叠加文字")
                
        else:
            print(f"❌ 模板ID {template_id} 不存在")
            
        # 显示所有可用模板
        cursor.execute("""
            SELECT id, name, template_type, font_size 
            FROM image_templates ORDER BY id
        """)
        all_templates = cursor.fetchall()
        
        print(f"\n📋 所有可用模板:")
        for tid, name, ttype, size in all_templates:
            current_mark = " ← 当前使用" if tid == template_id else ""
            print(f"   - ID:{tid} '{name}' ({ttype}, 字号{size}){current_mark}")
            
    except Exception as e:
        print(f"❌ 查询出错: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def switch_template(template_id):
    """切换到指定模板"""
    try:
        conn = sqlite3.connect("app/wechat_matrix.db")
        cursor = conn.cursor()
        
        # 检查模板是否存在
        cursor.execute("SELECT name FROM image_templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        
        if not template:
            print(f"❌ 模板ID {template_id} 不存在")
            return
            
        # 更新模板状态
        cursor.execute("""
            UPDATE template_state 
            SET current_image_template_id = ?, 
                image_template_enabled = 1,
                updated_at = datetime('now')
            WHERE id = 1
        """, (template_id,))
        
        conn.commit()
        print(f"✅ 已切换到模板: {template[0]} (ID: {template_id})")
        
    except Exception as e:
        print(f"❌ 切换失败: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            template_id = int(sys.argv[1])
            switch_template(template_id)
            print()
        except ValueError:
            print("❌ 请输入有效的模板ID数字")
            
    show_current_template_status()