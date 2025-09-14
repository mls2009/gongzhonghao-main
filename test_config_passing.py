#!/usr/bin/env python3
"""
测试配置传递的完整流程
"""

import requests
import json
import sqlite3

def compare_config_chain():
    """对比配置传递链条中的每一环节"""
    
    print("🔍 配置传递链条完整分析")
    print("="*60)
    
    # 1. 数据库中的原始配置
    print("📊 步骤1: 数据库中的原始配置")
    conn = sqlite3.connect("app/wechat_matrix.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, font_size, line_height, text_style, background_style FROM image_templates WHERE id = 3")
    db_config = cursor.fetchone()
    conn.close()
    
    if db_config:
        template_id, name, font_size, line_height, text_style, bg_style = db_config
        print(f"   ✅ 模板 '{name}' (ID: {template_id})")
        print(f"   - 字体大小: {font_size}")
        print(f"   - 行高: {line_height}")
        print(f"   - 文字样式: {text_style}")
        print(f"   - 背景样式: {bg_style}")
    else:
        print("   ❌ 数据库中未找到模板")
        return
    
    # 2. API返回给前端的配置
    print(f"\n📡 步骤2: API返回给前端的配置")
    try:
        response = requests.get("http://localhost:8000/api/template-materials/generate-template-image-for-material?material_id=1", 
                              json={}, timeout=10)
        if response.status_code == 200:
            api_data = response.json()
            if api_data.get('success'):
                template_config = api_data.get('template_config', {})
                print(f"   ✅ API调用成功")
                print(f"   - 字体大小: {template_config.get('font_size')}")
                print(f"   - 行高: {template_config.get('line_height')}")
                print(f"   - 文字样式: {template_config.get('text_style')}")
                print(f"   - 背景样式: {template_config.get('background_style')}")
                print(f"   - 文字颜色: {template_config.get('text_color')}")
            else:
                print(f"   ❌ API返回失败: {api_data.get('message')}")
                return
        else:
            print(f"   ❌ API调用失败: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ API调用出错: {str(e)}")
        return
    
    # 3. 对比分析
    print(f"\n🔎 步骤3: 对比分析")
    db_font_size = int(font_size)
    api_font_size = template_config.get('font_size')
    
    db_line_height = float(line_height)
    api_line_height = template_config.get('line_height')
    
    if db_font_size == api_font_size:
        print(f"   ✅ 字体大小传递正确: {db_font_size} → {api_font_size}")
    else:
        print(f"   ❌ 字体大小传递错误: DB={db_font_size}, API={api_font_size}")
    
    if abs(db_line_height - api_line_height) < 0.01:
        print(f"   ✅ 行高传递正确: {db_line_height} → {api_line_height}")
    else:
        print(f"   ❌ 行高传递错误: DB={db_line_height}, API={api_line_height}")
    
    if text_style == template_config.get('text_style'):
        print(f"   ✅ 文字样式传递正确: {text_style}")
    else:
        print(f"   ❌ 文字样式传递错误: DB={text_style}, API={template_config.get('text_style')}")
    
    # 4. 前端应该使用的配置
    print(f"\n🎨 步骤4: 前端Canvas应该使用的配置")
    print(f"   前端 drawTexts 函数会收到这些参数:")
    print(f"   - fontSize: {api_font_size} (如果undefined则默认60)")
    print(f"   - lineHeight: {api_line_height} (如果undefined则默认1.2)")
    print(f"   - actualLineHeight: {api_font_size} * {api_line_height} = {api_font_size * api_line_height}")
    
    # 5. 潜在问题分析
    print(f"\n⚠️  步骤5: 潜在问题分析")
    
    # 检查前端默认值问题
    if api_font_size == 60:
        print(f"   🚨 警告: 字体大小为60，可能使用了前端默认值而非数据库配置!")
        print(f"   数据库配置: {db_font_size}, API传递: {api_font_size}")
    
    if api_line_height == 1.2:
        print(f"   🚨 警告: 行高为1.2，可能使用了前端默认值而非数据库配置!")
        print(f"   数据库配置: {db_line_height}, API传递: {api_line_height}")
    
    # 计算实际行间距
    actual_line_spacing = api_font_size * api_line_height
    print(f"\n📏 实际渲染效果预测:")
    print(f"   - 字体大小: {api_font_size}px")
    print(f"   - 行间距: {actual_line_spacing}px")
    print(f"   - 总高度(3行): {actual_line_spacing * 2}px")

if __name__ == "__main__":
    compare_config_chain()