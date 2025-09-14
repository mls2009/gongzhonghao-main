#!/usr/bin/env python3
"""
测试模板配置修复后的效果
"""

import requests
import sqlite3

def test_template_fix():
    """测试模板配置是否正确传递和应用"""
    
    print("🧪 测试模板配置修复效果")
    print("="*50)
    
    # 1. 显示当前模板配置
    print("📊 当前数据库中的模板配置:")
    conn = sqlite3.connect("app/wechat_matrix.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, font_size, line_height FROM image_templates WHERE id = 3")
    template = cursor.fetchone()
    conn.close()
    
    if template:
        template_id, name, font_size, line_height = template
        print(f"   模板: '{name}' (ID: {template_id})")
        print(f"   数据库字体大小: {font_size}")
        print(f"   数据库行高: {line_height}")
    else:
        print("   未找到模板")
        return
    
    # 2. 测试API传递
    print(f"\n📡 测试API配置传递:")
    try:
        response = requests.post("http://localhost:8000/api/template-materials/generate-template-image-for-material?material_id=1")
        if response.status_code == 200:
            data = response.json()
            config = data.get('template_config', {})
            print(f"   API返回的字体大小: {config.get('font_size')}")
            print(f"   API返回的行高: {config.get('line_height')}")
            
            # 验证是否正确
            if config.get('font_size') == font_size:
                print(f"   ✅ 字体大小传递正确")
            else:
                print(f"   ❌ 字体大小传递错误: 期望{font_size}, 实际{config.get('font_size')}")
                
            expected_line_height = float(line_height)
            actual_line_height = config.get('line_height')
            if abs(expected_line_height - actual_line_height) < 0.01:
                print(f"   ✅ 行高传递正确")
            else:
                print(f"   ❌ 行高传递错误: 期望{expected_line_height}, 实际{actual_line_height}")
                
        else:
            print(f"   ❌ API调用失败: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API测试出错: {str(e)}")
        
    # 3. 显示预期的Canvas渲染效果
    print(f"\n🎨 预期的Canvas渲染效果:")
    expected_font = font_size
    expected_line_height = float(line_height)
    expected_actual_line_height = expected_font * expected_line_height
    
    print(f"   字体大小: {expected_font}px")
    print(f"   行高倍数: {expected_line_height}")
    print(f"   实际行间距: {expected_actual_line_height}px")
    print(f"   三行文字总高度: {expected_actual_line_height * 2}px")
    
    # 4. 对比修复前后
    print(f"\n📈 修复前后对比:")
    print(f"   修复前可能使用: 字体60px, 行高1.2 (硬编码默认值)")
    print(f"   修复后应该使用: 字体{expected_font}px, 行高{expected_line_height} (数据库配置)")
    print(f"   行间距差异: {60 * 1.2}px → {expected_actual_line_height}px")
    
    return True

if __name__ == "__main__":
    test_template_fix()