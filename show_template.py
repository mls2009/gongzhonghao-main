#!/usr/bin/env python3
import sqlite3

def show_current_template():
    conn = sqlite3.connect("app/wechat_matrix.db")
    cursor = conn.cursor()
    
    print("🎯 当前模板使用情况:")
    print("="*50)
    
    # 获取当前模板状态
    cursor.execute("SELECT current_image_template_id, image_template_enabled FROM template_state WHERE id = 1")
    state = cursor.fetchone()
    
    if state:
        template_id, enabled = state
        print(f"📊 模板状态: {'启用' if enabled else '未启用'}, 模板ID: {template_id}")
        
        if enabled and template_id:
            cursor.execute("SELECT name, template_type, text_style, font_size FROM image_templates WHERE id = ?", (template_id,))
            template = cursor.fetchone()
            if template:
                name, ttype, style, size = template
                print(f"🎨 当前模板: '{name}' (类型:{ttype}, 样式:{style}, 字号:{size})")
    
    # 显示所有模板
    cursor.execute("SELECT id, name, template_type, font_size FROM image_templates ORDER BY id")
    templates = cursor.fetchall()
    print(f"\n📋 所有可用模板:")
    for tid, name, ttype, size in templates:
        current = " ← 当前" if state and tid == state[0] else ""
        print(f"   ID:{tid} '{name}' ({ttype}, 字号{size}){current}")
    
    conn.close()

if __name__ == "__main__":
    show_current_template()