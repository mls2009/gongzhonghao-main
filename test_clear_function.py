#!/usr/bin/env python3
"""
测试一键清空功能的脚本
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_clear_function():
    """测试一键清空功能"""
    print("🧪 开始测试一键清空功能...")
    
    # 1. 首先查看当前已发布的素材
    print("\n1️⃣ 查看当前已发布的素材:")
    response = requests.get(f"{BASE_URL}/api/materials?status=published")
    if response.status_code == 200:
        published_materials = response.json()
        print(f"   当前已发布素材数量: {len(published_materials)}")
        for material in published_materials:
            print(f"   - ID: {material['id']}, 标题: {material['title']}")
    else:
        print(f"   获取已发布素材失败: {response.status_code}")
        return
    
    if len(published_materials) == 0:
        print("   没有已发布的素材，无法测试清空功能")
        return
    
    # 2. 执行一键清空
    print("\n2️⃣ 执行一键清空:")
    response = requests.post(f"{BASE_URL}/api/materials/batch-clear")
    if response.status_code == 200:
        result = response.json()
        print(f"   清空结果: {result}")
    else:
        print(f"   清空失败: {response.status_code} - {response.text}")
        return
    
    # 3. 验证清空后的状态
    print("\n3️⃣ 验证清空后的状态:")
    response = requests.get(f"{BASE_URL}/api/materials?status=published")
    if response.status_code == 200:
        published_after_clear = response.json()
        print(f"   清空后已发布素材数量: {len(published_after_clear)}")
    
    # 4. 查看隐藏状态的素材
    print("\n4️⃣ 查看隐藏状态的素材:")
    response = requests.get(f"{BASE_URL}/api/materials?status=hidden")
    if response.status_code == 200:
        hidden_materials = response.json()
        print(f"   隐藏状态素材数量: {len(hidden_materials)}")
        for material in hidden_materials:
            print(f"   - ID: {material['id']}, 标题: {material['title']}, 状态: {material['status']}")
    
    print("\n✅ 测试完成！")
    print("\n📝 使用说明:")
    print("   1. 页面上的'已发布'列表现在应该是空的")
    print("   2. 重新扫描素材库时，如果文件还在，这些记录会被恢复")
    print("   3. 数据实际上没有被删除，只是被隐藏了")

if __name__ == "__main__":
    test_clear_function()