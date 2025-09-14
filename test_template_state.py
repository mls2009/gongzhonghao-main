#!/usr/bin/env python3
"""
测试模板状态功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from models.database import get_db, TemplateState, ImageTemplate
from datetime import datetime

def test_template_state():
    """测试模板状态创建和更新"""
    
    print("🔍 测试模板状态功能...")
    
    # 获取数据库会话
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        print("1. 检查现有模板状态...")
        existing_state = db.query(TemplateState).first()
        if existing_state:
            print(f"   现有状态ID: {existing_state.id}")
            print(f"   图片模板ID: {existing_state.current_image_template_id}")
            print(f"   图片模板启用: {existing_state.image_template_enabled}")
        else:
            print("   没有现有状态")
        
        print("2. 创建新的模板状态...")
        if existing_state:
            state = existing_state
        else:
            state = TemplateState()
            db.add(state)
        
        # 更新状态
        state.current_image_template_id = 1
        state.image_template_enabled = True
        state.image_template_mode = 'insert'
        state.updated_at = datetime.now()
        
        db.commit()
        db.refresh(state)
        
        print(f"   ✅ 状态更新成功")
        print(f"   - ID: {state.id}")
        print(f"   - 图片模板ID: {state.current_image_template_id}")
        print(f"   - 图片模板启用: {state.image_template_enabled}")
        print(f"   - 模板模式: {state.image_template_mode}")
        
        print("3. 验证数据库记录...")
        # 重新查询验证
        db.commit()  # 确保提交
        verification_state = db.query(TemplateState).first()
        if verification_state:
            print(f"   ✅ 数据库验证成功")
            print(f"   - 图片模板ID: {verification_state.current_image_template_id}")
            print(f"   - 启用状态: {verification_state.image_template_enabled}")
        else:
            print(f"   ❌ 数据库验证失败：未找到记录")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
        
    finally:
        db.close()

def test_get_or_create_function():
    """测试 get_or_create_template_state 函数"""
    print("\n🔍 测试 get_or_create_template_state 函数...")
    
    # 导入函数
    sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'routers'))
    from template_materials import get_or_create_template_state
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 清空现有状态
        db.query(TemplateState).delete()
        db.commit()
        print("   清空了现有状态")
        
        # 测试创建
        state = get_or_create_template_state(db)
        print(f"   ✅ 函数执行成功，返回状态ID: {state.id}")
        
        # 验证数据库
        verification = db.query(TemplateState).first()
        if verification:
            print(f"   ✅ 数据库记录创建成功，ID: {verification.id}")
        else:
            print(f"   ❌ 数据库记录创建失败")
        
        return True
        
    except Exception as e:
        print(f"❌ 函数测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 开始测试模板状态功能...")
    print("="*50)
    
    # 测试1: 直接操作
    success1 = test_template_state()
    
    # 测试2: 函数测试
    success2 = test_get_or_create_function()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！")
    else:
        print("\n❌ 部分测试失败")