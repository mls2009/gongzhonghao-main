def extract_region_from_title(title: str) -> str:
    """从标题中提取地区信息 - 提取年字和央国企之间的文字"""
    import re
    # 使用正则表达式提取年字和央国企之间的文字
    match = re.search(r"年(.+?)央国企", title)
    if match:
        return match.group(1)
    
    # 如果没有找到，尝试其他模式
    match = re.search(r"年(.+?)国企", title)
    if match:
        return match.group(1)
    
    # 如果都没有找到，返回默认值
    return "全国"
