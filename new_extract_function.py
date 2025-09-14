def extract_region_from_title(title: str) -> str:
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
    return '全国'
