#!/usr/bin/env python3
"""
调试模板缓存问题
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from models.database import get_db, ImageTemplate, TemplateState
import requests

def test_direct_db_access():
    """直接测试数据库访问"""
    print("🔍 直接测试数据库访问...")
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 直接查询模板
        template = db.query(ImageTemplate).filter(ImageTemplate.id == 1).first()
        if template:
            print(f"   数据库直接查询结果:")
            print(f"   - ID: {template.id}")
            print(f"   - 名称: {template.name}")
            print(f"   - 样式: {template.text_style}")
            print(f"   - 背景: {template.background_style}")
            print(f"   - 字体大小: {template.font_size}")
        else:
            print("   未找到模板")
            
        # 查询模板状态
        state = db.query(TemplateState).first()
        if state:
            print(f"   模板状态:")
            print(f"   - 图片模板ID: {state.current_image_template_id}")
            print(f"   - 启用状态: {state.image_template_enabled}")
        else:
            print("   未找到模板状态")
            
    finally:
        db.close()

def test_api_access():
    """测试API访问"""
    print("\n🔍 测试API访问...")
    
    try:
        response = requests.get("http://localhost:8000/api/template-materials/get-current-image-template")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                template = data.get('template', {})
                print(f"   API查询结果:")
                print(f"   - ID: {template.get('id')}")
                print(f"   - 名称: {template.get('name')}")
                print(f"   - 样式: {template.get('text_style')}")
                print(f"   - 背景: {template.get('background_style')}")
                print(f"   - 字体大小: {template.get('font_size')}")
            else:
                print(f"   API返回失败: {data.get('message')}")
        else:
            print(f"   API请求失败: {response.status_code}")
    except Exception as e:
        print(f"   API测试出错: {str(e)}")

def compare_results():
    """对比结果"""
    print("\n📊 对比数据库和API结果...")
    
    # 数据库结果
    db_gen = get_db()
    db = next(db_gen)
    db_template = None
    
    try:
        db_template = db.query(ImageTemplate).filter(ImageTemplate.id == 1).first()
    finally:
        db.close()
    
    # API结果
    api_template = None
    try:
        response = requests.get("http://localhost:8000/api/template-materials/get-current-image-template")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                api_template = data.get('template', {})
    except:
        pass
    
    if db_template and api_template:
        print("   对比结果:")
        fields = ['name', 'text_style', 'background_style', 'font_size']
        
        for field in fields:
            db_value = getattr(db_template, field, None)
            api_value = api_template.get(field, None)
            
            if db_value == api_value:
                print(f"   ✅ {field}: {db_value}")
            else:
                print(f"   ❌ {field}: DB={db_value}, API={api_value}")
    else:
        print("   无法获取完整数据进行对比")

if __name__ == "__main__":
    print("🚀 开始调试模板缓存问题...")
    print("="*50)
    
    test_direct_db_access()
    test_api_access()
    compare_results()