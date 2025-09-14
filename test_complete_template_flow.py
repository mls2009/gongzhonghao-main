#!/usr/bin/env python3
"""
完整测试模板配置和应用流程
"""

import requests
import json
import sys
import os
import time

BASE_URL = "http://localhost:8000"

def test_complete_template_flow():
    """测试完整的模板流程"""
    
    print("🚀 开始测试完整的模板配置和应用流程...")
    print("="*60)
    
    try:
        # 1. 测试获取当前模板状态
        print("1️⃣ 测试获取当前模板状态...")
        response = requests.get(f"{BASE_URL}/api/template-materials/current-templates")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 当前模板状态: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"   ❌ 获取模板状态失败: {response.status_code}")
            return False
        
        # 2. 测试应用图片模板
        print("\n2️⃣ 测试应用图片模板...")
        response = requests.post(f"{BASE_URL}/api/template-materials/apply-image-template/1")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 应用模板成功: {data['message']}")
            print(f"   模板ID: {data['template_id']}, 模式: {data['mode']}")
        else:
            print(f"   ❌ 应用模板失败: {response.status_code}")
            print(f"   错误: {response.text}")
            return False
        
        # 等待一下确保数据库更新
        time.sleep(1)
        
        # 3. 再次获取模板状态验证更新
        print("\n3️⃣ 验证模板状态更新...")
        response = requests.get(f"{BASE_URL}/api/template-materials/current-templates")
        if response.status_code == 200:
            data = response.json()
            image_mode = data.get('image_template_mode', {})
            if not image_mode.get('is_random_mode') and image_mode.get('current_template_id') == 1:
                print(f"   ✅ 模板状态更新成功")
                print(f"   当前图片模板: {image_mode.get('current_template_name')} (ID: {image_mode.get('current_template_id')})")
                print(f"   模式: {image_mode.get('mode')}")
            else:
                print(f"   ❌ 模板状态更新失败")
                print(f"   实际状态: {json.dumps(image_mode, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"   ❌ 获取更新后状态失败: {response.status_code}")
            return False
        
        # 4. 测试获取当前图片模板详情
        print("\n4️⃣ 测试获取当前图片模板详情...")
        response = requests.get(f"{BASE_URL}/api/template-materials/get-current-image-template")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                template = data.get('template', {})
                print(f"   ✅ 获取模板详情成功")
                print(f"   模板名称: {template.get('name')}")
                print(f"   模板类型: {template.get('template_type')}")
                print(f"   文字样式: {template.get('text_style')}")
                print(f"   背景样式: {template.get('background_style')}")
            else:
                print(f"   ❌ 获取模板详情失败: {data.get('message')}")
                return False
        else:
            print(f"   ❌ 请求模板详情失败: {response.status_code}")
            return False
        
        # 5. 测试模板状态切换
        print("\n5️⃣ 测试退出当前模板...")
        response = requests.post(f"{BASE_URL}/api/template-materials/exit-current-template")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 退出模板成功: {data['message']}")
        else:
            print(f"   ❌ 退出模板失败: {response.status_code}")
            return False
        
        # 6. 验证随机模式
        print("\n6️⃣ 验证随机模式...")
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/api/template-materials/current-templates")
        if response.status_code == 200:
            data = response.json()
            image_mode = data.get('image_template_mode', {})
            if image_mode.get('is_random_mode'):
                print(f"   ✅ 成功切换到随机模式")
            else:
                print(f"   ❌ 随机模式切换失败")
                print(f"   当前状态: {json.dumps(image_mode, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"   ❌ 验证随机模式失败: {response.status_code}")
            return False
        
        print(f"\n🎉 完整模板流程测试成功！")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保应用程序正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_database_direct():
    """直接测试数据库状态"""
    print("\n📊 直接检查数据库状态...")
    
    import sqlite3
    try:
        conn = sqlite3.connect("wechat_matrix.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM template_state;")
        rows = cursor.fetchall()
        
        if rows:
            print(f"   ✅ 数据库中有 {len(rows)} 条模板状态记录")
            for row in rows:
                print(f"   记录: {row}")
        else:
            print("   ⚠️  数据库中没有模板状态记录")
        
        cursor.execute("SELECT * FROM image_templates;")
        templates = cursor.fetchall()
        print(f"   📋 可用图片模板: {len(templates)} 个")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 数据库检查失败: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # 检查数据库状态
    test_database_direct()
    
    # 测试完整流程
    if test_complete_template_flow():
        print("\n✅ 所有测试通过！模板系统工作正常")
    else:
        print("\n❌ 部分测试失败，请检查问题")
    
    # 最终数据库状态
    test_database_direct()