#!/usr/bin/env python3
"""
实时模板调试监控系统
"""

import sys
import os
import time
import requests
import sqlite3
from datetime import datetime
import json

# 添加app路径以便导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def print_separator(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def get_db_template_info():
    """直接从数据库获取模板信息"""
    try:
        conn = sqlite3.connect("app/wechat_matrix.db")
        cursor = conn.cursor()
        
        # 获取所有模板
        cursor.execute("SELECT id, name, template_type, text_style, background_style, font_size, text_color FROM image_templates ORDER BY id;")
        templates = cursor.fetchall()
        
        # 获取当前模板状态
        cursor.execute("SELECT current_image_template_id, image_template_enabled, image_template_mode, updated_at FROM template_state WHERE id = 1;")
        state = cursor.fetchone()
        
        conn.close()
        
        return {
            'templates': templates,
            'state': state
        }
    except Exception as e:
        return {'error': str(e)}

def get_api_template_info():
    """通过API获取模板信息"""
    try:
        # 获取当前模板状态
        response1 = requests.get("http://localhost:8000/api/template-materials/current-templates", timeout=5)
        current_status = response1.json() if response1.status_code == 200 else None
        
        # 获取当前图片模板详情
        response2 = requests.get("http://localhost:8000/api/template-materials/get-current-image-template", timeout=5)
        template_details = response2.json() if response2.status_code == 200 else None
        
        return {
            'current_status': current_status,
            'template_details': template_details
        }
    except Exception as e:
        return {'error': str(e)}

def display_template_comparison():
    """显示模板信息对比"""
    print_separator("当前模板状态对比分析")
    
    # 数据库信息
    print("📊 数据库直接查询:")
    db_info = get_db_template_info()
    
    if 'error' in db_info:
        print(f"   ❌ 数据库查询失败: {db_info['error']}")
    else:
        if db_info['templates']:
            print("   可用模板列表:")
            for template in db_info['templates']:
                template_id, name, template_type, text_style, bg_style, font_size, text_color = template
                print(f"   - ID:{template_id} | 名称:'{name}' | 类型:{template_type} | 样式:{text_style} | 背景:{bg_style} | 字号:{font_size}")
        
        if db_info['state']:
            current_id, enabled, mode, updated = db_info['state']
            print(f"   当前状态: 模板ID={current_id}, 启用={bool(enabled)}, 模式={mode}, 更新时间={updated}")
        else:
            print("   ⚠️  没有模板状态记录")
    
    # API信息
    print("\n🌐 API查询结果:")
    api_info = get_api_template_info()
    
    if 'error' in api_info:
        print(f"   ❌ API查询失败: {api_info['error']}")
    else:
        if api_info['current_status']:
            image_mode = api_info['current_status'].get('image_template_mode', {})
            print(f"   当前图片模板状态:")
            print(f"   - 随机模式: {image_mode.get('is_random_mode')}")
            print(f"   - 模板ID: {image_mode.get('current_template_id')}")
            print(f"   - 模板名称: '{image_mode.get('current_template_name')}'")
            print(f"   - 模式: {image_mode.get('mode')}")
        
        if api_info['template_details'] and api_info['template_details'].get('success'):
            template = api_info['template_details']['template']
            print(f"   当前模板详细信息:")
            print(f"   - ID: {template.get('id')}")
            print(f"   - 名称: '{template.get('name')}'")
            print(f"   - 类型: {template.get('template_type')}")
            print(f"   - 文字样式: {template.get('text_style')}")
            print(f"   - 背景样式: {template.get('background_style')}")
            print(f"   - 字体大小: {template.get('font_size')}")
            print(f"   - 文字颜色: {template.get('text_color')}")
    
    # 一致性检查
    print("\n🔎 一致性检查:")
    if 'error' not in db_info and 'error' not in api_info and db_info['state'] and api_info['current_status']:
        db_id = db_info['state'][0]
        api_id = api_info['current_status']['image_template_mode'].get('current_template_id')
        
        if db_id == api_id:
            print(f"   ✅ 数据库和API一致，都使用模板ID: {db_id}")
        else:
            print(f"   ❌ 数据不一致! 数据库ID:{db_id}, API ID:{api_id}")
    else:
        print("   ⚠️  无法进行一致性检查")

def test_template_generation(material_id=1):
    """测试模板生成API"""
    print_separator(f"测试素材{material_id}的模板生成")
    
    try:
        response = requests.post(
            f"http://localhost:8000/api/template-materials/generate-template-image-for-material?material_id={material_id}",
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"📡 API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 模板生成配置成功获取:")
                print(f"   - 模板名称: '{data.get('template_name')}'")
                print(f"   - 素材ID: {data.get('material_id')}")
                print(f"   - 模式: {data.get('mode')}")
                print(f"   - 输出路径: {data.get('output_path')}")
                print(f"   - 文字内容: {data.get('text_lines')}")
                
                config = data.get('template_config', {})
                print(f"   - 模板配置:")
                print(f"     * 文字样式: {config.get('text_style')}")
                print(f"     * 背景样式: {config.get('background_style')}")
                print(f"     * 字体大小: {config.get('font_size')}")
                print(f"     * 文字颜色: {config.get('text_color')}")
            else:
                print(f"❌ 模板生成失败: {data.get('message')}")
        else:
            print(f"❌ API调用失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试过程出错: {str(e)}")

def monitor_mode():
    """监控模式 - 持续显示模板状态"""
    print_separator("进入实时监控模式")
    print("🔄 每5秒更新一次，按Ctrl+C退出...")
    
    try:
        while True:
            os.system('clear')  # 清屏 (macOS/Linux)
            print(f"⏰ 实时监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            display_template_comparison()
            
            print(f"\n💡 提示: 如果看到模板没有变化，请:")
            print(f"   1. 检查是否在正确的页面应用了模板")
            print(f"   2. 确认模板状态是否正确设置")
            print(f"   3. 尝试重新应用模板")
            
            time.sleep(5)
    except KeyboardInterrupt:
        print(f"\n\n👋 监控结束")

def main():
    """主函数"""
    print("🚀 模板调试监控系统启动")
    print("选择模式:")
    print("1. 显示当前状态")
    print("2. 测试模板生成")
    print("3. 实时监控模式")
    print("4. 全面检查")
    
    try:
        choice = input("\n请输入选择 (1-4): ").strip()
        
        if choice == '1':
            display_template_comparison()
        elif choice == '2':
            material_id = input("请输入素材ID (默认1): ").strip() or "1"
            test_template_generation(int(material_id))
        elif choice == '3':
            monitor_mode()
        elif choice == '4':
            display_template_comparison()
            test_template_generation(1)
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print(f"\n\n👋 程序退出")
    except Exception as e:
        print(f"\n❌ 程序出错: {str(e)}")

if __name__ == "__main__":
    main()