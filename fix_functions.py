#!/usr/bin/env python3
import re

# 读取原文件
with open('app/routers/xiaohongshu_materials.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 新的区域提取函数
new_extract_function = '''def extract_region_from_title(title: str) -> str:
    """从标题中提取地区信息"""
    # 使用正则表达式提取"年"和"央国企"之间的内容
    pattern = r'年([^央国企]+?)(?:央国企|央企|国企)'
    match = re.search(pattern, title)
    
    if match:
        region = match.group(1).strip().replace(" ", "")
        return region
    
    # 备用方案：直接查找已知地区名
    known_regions = [
        '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '苏州',
        '天津', '重庆', '青岛', '大连', '厦门', '宁波', '无锡', '长沙', '郑州', '合肥',
        '江苏', '浙江', '广东', '山东', '河北', '河南', '湖北', '湖南', '四川', '福建',
        '安徽', '江西', '辽宁', '黑龙江', '吉林', '山西', '陕西', '甘肃', '青海', '内蒙古',
        '新疆', '西藏', '宁夏', '海南', '云南', '贵州', '台湾', '香港', '澳门'
    ]
    
    for region in known_regions:
        if region in title:
            return region
    return '全国''

# 新的内容生成函数
new_content_function = '''async def generate_template_content(template: ContentTemplate, material_title: str) -> str:
    """根据模板生成内容 - 按照要求格式生成"""
    content_parts = []
    
    # 提取日期
    date_match = re.search(r'(\d+月\d+日)', material_title)
    if date_match:
        content_parts.append(date_match.group(1))
    
    # 提取区域并生成第二行
    region = extract_region_from_title(material_title)
    content_parts.append(f"{region}国企")
    
    # 添加话题标签
    topics = [
        f"#{region}国企",
        f"#{region}国企招聘", 
        "#全国国企",
        "#全国国企招聘"
    ]
    
    # 组合内容
    content = '\\n'.join(content_parts)
    content += '\\n\\n' + ' '.join(topics)
    
    return content'''

# 替换区域提取函数
pattern1 = r'def extract_region_from_title\(title: str\) -> str:.*?return \'全国\''
content = re.sub(pattern1, new_extract_function, content, flags=re.DOTALL)

# 替换内容生成函数
pattern2 = r'async def generate_template_content\(template: ContentTemplate, material_title: str\) -> str:.*?return \'\\n\\n\'.join\(content_parts\) if content_parts else \'\''
content = re.sub(pattern2, new_content_function, content, flags=re.DOTALL)

# 写回文件
with open('app/routers/xiaohongshu_materials.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("函数替换完成！")
