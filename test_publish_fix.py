#!/usr/bin/env python3
"""
测试小红书素材发布修复效果
"""

import sys
import os
import asyncio
import httpx
import json

# 添加app目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_direct_publish():
    """测试直接发布单个素材"""
    print("🧪 开始测试直接发布功能...")
    
    # 测试数据
    test_material_id = 1
    test_data = {
        "add_product": False,
        "default_mode": "insert"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. 首先测试获取模板配置
            print(f"📡 测试获取素材 {test_material_id} 的模板配置...")
            config_response = await client.post(
                f"http://localhost:8000/api/template-materials/generate-template-image-for-material?material_id={test_material_id}"
            )
            
            print(f"📄 模板配置响应状态: {config_response.status_code}")
            
            if config_response.status_code == 200:
                config_data = config_response.json()
                print(f"✅ 模板配置获取成功: {json.dumps(config_data, indent=2, ensure_ascii=False)}")
            else:
                print(f"❌ 模板配置获取失败: {config_response.text}")
                return
            
            # 2. 测试直接发布（不实际执行浏览器操作）
            print(f"🚀 测试直接发布素材 {test_material_id}...")
            publish_response = await client.post(
                f"http://localhost:8000/api/xiaohongshu-materials/{test_material_id}/direct-publish",
                json=test_data
            )
            
            print(f"📄 发布响应状态: {publish_response.status_code}")
            
            if publish_response.status_code == 200:
                publish_data = publish_response.json()
                print(f"✅ 发布请求成功: {json.dumps(publish_data, indent=2, ensure_ascii=False)}")
                
                # 分析响应
                if publish_data.get("success"):
                    print("🎉 发布成功！")
                    if publish_data.get("template_applied"):
                        print("✅ 图片模板已应用")
                    else:
                        print("⚠️  图片模板未应用")
                else:
                    print(f"❌ 发布失败: {publish_data.get('message')}")
            else:
                print(f"❌ 发布请求失败: {publish_response.text}")
                
        except Exception as e:
            print(f"💥 测试过程中发生异常: {str(e)}")

async def test_template_state():
    """测试模板状态"""
    print("🧪 检查数据库模板状态...")
    
    from models.database import get_db, TemplateState, ImageTemplate
    
    db = next(get_db())
    
    # 检查模板状态
    template_state = db.query(TemplateState).first()
    if template_state:
        print(f"📋 模板状态:")
        print(f"   - 图片模板启用: {template_state.image_template_enabled}")
        print(f"   - 当前图片模板ID: {template_state.current_image_template_id}")
        print(f"   - 图片模板模式: {template_state.image_template_mode}")
        print(f"   - 内容模板启用: {template_state.content_template_enabled}")
        
        if template_state.current_image_template_id:
            template = db.query(ImageTemplate).filter(
                ImageTemplate.id == template_state.current_image_template_id
            ).first()
            if template:
                print(f"   - 当前模板名称: {template.name}")
                print(f"   - 当前模板类型: {template.template_type}")
            else:
                print(f"   ❌ 当前模板ID {template_state.current_image_template_id} 不存在")
    else:
        print("❌ 未找到模板状态记录")
    
    # 检查图片模板数量
    templates = db.query(ImageTemplate).all()
    print(f"📊 数据库中共有 {len(templates)} 个图片模板")

async def main():
    """主测试函数"""
    print("=" * 50)
    print("🚀 小红书素材发布修复效果测试")
    print("=" * 50)
    
    # 测试1: 检查模板状态
    await test_template_state()
    print()
    
    # 测试2: 测试API调用
    await test_direct_publish()
    print()
    
    print("=" * 50)
    print("✅ 测试完成")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())