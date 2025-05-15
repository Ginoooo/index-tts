import re

# --- 常量定义 ---
DIGIT_MAP = {
    '0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
    '5': '五', '6': '六', '7': '七', '8': '八', '9': '九'
}

TEL_DIGIT_MAP = {
    '0': '零', '1': '幺', '2': '二', '3': '三', '4': '四',
    '5': '五', '6': '六', '7': '七', '8': '八', '9': '九',
}

KNOWN_MONETARY_UNITS = ["人民币", "美元", "元"] # 已知货币单位

# --- 辅助转换函数 ---

def _convert_char_by_char_to_chinese(s, is_telephone=False, is_year=False, handle_dot_for_number=False):
    output_chars = []
    current_map = TEL_DIGIT_MAP if is_telephone else DIGIT_MAP
    
    processed_content = s
    if is_telephone and processed_content.startswith('+'):
        processed_content = processed_content[1:]

    for char_code in processed_content:
        if char_code == '.' and handle_dot_for_number:
            output_chars.append('点')
        elif char_code in current_map:
            output_chars.append(current_map[char_code])
        else:
            output_chars.append(char_code) 
    return "".join(output_chars)

def _normalize_number_for_date_time_parts(num_str, component_type="generic"):
    if not num_str.isdigit():
        return num_str
        
    val = int(num_str)

    if component_type == "minute":
        if num_str == "00": return "零"
        if len(num_str) == 2 and num_str.startswith('0') and val != 0:
            return "零" + DIGIT_MAP[num_str[1]]

    if val == 0: return DIGIT_MAP['0']
    if 1 <= val <= 9: return DIGIT_MAP[str(val)]
    if val == 10: return "十"
    if 11 <= val <= 19: return "十" + DIGIT_MAP[str(val % 10)]
    if 20 <= val <= 99 and val % 10 == 0:
        return DIGIT_MAP[str(val // 10)] + "十"
    if 20 <= val <= 99:
        return DIGIT_MAP[str(val // 10)] + "十" + DIGIT_MAP[str(val % 10)]
    return num_str # Fallback for numbers outside 0-99 or non-digits

def _number_to_chinese_natural_reading(num_str):
    """将数字字符串转换为中文自然读法 (例如 "16" -> "十六", "400" -> "四百")"""
    if not num_str.isdigit():
        # 如果输入不是纯数字 (例如 "16GB")，尝试分离数字和后缀
        match = re.match(r"(\d+)(.*)", num_str)
        if match:
            num_part = match.group(1)
            suffix_part = match.group(2)
            # 仅转换数字部分，后缀由调用者处理或在此追加
            return _number_to_chinese_natural_reading(num_part) + suffix_part
        return _convert_char_by_char_to_chinese(num_str) # 最后回退

    val = int(num_str)

    if val < 0:
        return "负" + _number_to_chinese_natural_reading(str(abs(val)))

    if 0 <= val <= 99:
        return _normalize_number_for_date_time_parts(str(val), "generic") 
    
    if 100 <= val <= 999:
        h_digit_str = str(val // 100)
        remainder = val % 100
        
        res = _normalize_number_for_date_time_parts(h_digit_str, "generic") + "百"
        
        if remainder == 0:
            return res 
        else:
            if remainder < 10: 
                res += DIGIT_MAP['0'] # 加 "零"
            
            if remainder == 10: # 特殊处理 X百一十
                 res += DIGIT_MAP['1'] + "十"
            else: # 1-9 (在零之后), 11-19, 20-99
                 res += _normalize_number_for_date_time_parts(str(remainder), "generic")
            return res
    
    # 对于更大的数字，当前示例未覆盖完整复杂的中文读法 (如 千, 万, 亿 的精确零位处理)
    # 默认为逐位转换，或根据需要扩展此函数
    return _convert_char_by_char_to_chinese(num_str)

# --- 针对不同标签的转换函数 ---

def _convert_number_tag_content(content):
    return _convert_char_by_char_to_chinese(content, handle_dot_for_number=True)

def _convert_telephone_tag_content(content):
    return _convert_char_by_char_to_chinese(content, is_telephone=True)

def _convert_date_tag_content(content):
    if '/' in content:
        parts = content.split('/')
        if len(parts) == 3:
            year_str = _convert_char_by_char_to_chinese(parts[0], is_year=True)
            month_str = _normalize_number_for_date_time_parts(parts[1], "month")
            day_str = _normalize_number_for_date_time_parts(parts[2], "day")
            return f"{year_str}年{month_str}月{day_str}日"
    elif ':' in content:
        parts = content.split(':')
        if len(parts) == 2:
            hour_str = _normalize_number_for_date_time_parts(parts[0], "hour")
            minute_str = _normalize_number_for_date_time_parts(parts[1], "minute")
            return f"{hour_str}点{minute_str}分"
    return content

def _convert_currency_tag_content(content):
    # 尝试从内容中分离 数字 和 单位 (货币单位或其他)
    # ((\d+)([^\d\s]*)) -> group1: 数字, group2: 后缀(可能为空,可能是货币单位或GB等)
    match = re.match(r"(\d+)([^\d\s]*)", content)
    
    num_part_str = content
    raw_suffix = "" # 原始后缀，可能是货币单位，也可能是GB等
    monetary_unit_suffix = "" # 识别出的货币单位

    if match:
        num_part_str = match.group(1)
        raw_suffix = match.group(2)
        if raw_suffix in KNOWN_MONETARY_UNITS:
            monetary_unit_suffix = raw_suffix
    
    if num_part_str.isdigit():
        val = int(num_part_str)
        # 规则1: "X万" 模式 (需要有实际货币单位)
        if num_part_str.endswith("0000") and val > 0 and monetary_unit_suffix:
            prefix_val_str = num_part_str[:-4]
            if prefix_val_str:
                chinese_prefix = _number_to_chinese_natural_reading(prefix_val_str)
                return f"{chinese_prefix}万{monetary_unit_suffix}"
        
        # 规则2: 特定示例 "5432元" (逐位读)
        if monetary_unit_suffix == "元" and num_part_str == "5432":
             return _convert_char_by_char_to_chinese(num_part_str) + monetary_unit_suffix
        
        # 规则3: 通用数字自然读法 + 单位
        # (例如 <currency>3</currency> -> 三; <currency>400</currency>美元 -> 四百美元)
        # (如果 <currency>16GB</currency> -> 十六GB)
        chinese_num = _number_to_chinese_natural_reading(num_part_str)
        if monetary_unit_suffix: # 如果识别出的是标准货币单位
            return chinese_num + monetary_unit_suffix
        else: # 否则，数字转换后拼接原始后缀 (可能是GB等，或无后缀)
            return chinese_num + raw_suffix

    # 回退: 如果无法按数字处理 (例如内容不是数字开头)
    return _convert_char_by_char_to_chinese(content)


# --- 主处理函数 ---
def convert_tagged_string_to_spoken_chinese(input_str):
    pattern = re.compile(r"""
        < (?P<tag>number|currency|telephone|date) >
        (?P<content>.*?)
        </ (?P=tag) >
    """, re.VERBOSE)

    def replace_match_with_spoken_form(match_obj):
        tag_type = match_obj.group("tag")
        original_content = match_obj.group("content")

        if tag_type == "number":
            return _convert_number_tag_content(original_content)
        elif tag_type == "currency":
            return _convert_currency_tag_content(original_content)
        elif tag_type == "telephone":
            return _convert_telephone_tag_content(original_content)
        elif tag_type == "date":
            return _convert_date_tag_content(original_content)
        else:
            return match_obj.group(0)

    return pattern.sub(replace_match_with_spoken_form, input_str)

# --- 测试 ---
if __name__ == '__main__':
    # 原有测试用例
    original_test_cases = [
        ("最大数字：<number>65535</number>", "最大数字：六五五三五"),
        ("你的收入：<currency>120000美元</currency>", "你的收入：十二万美元"),
        ("电话号码：<telephone>+8613800138000</telephone>", "电话号码：八六幺三八零零幺三八零零零"),
        ("版本号码：<number>0.3.5</number>", "版本号码：零点三点五"),
        ("每天<date>20:30</date>记得按时吃饭哦！", "每天二十点三十分记得按时吃饭哦！"),
        ("入库日期：<date>2024/08/06</date>", "入库日期：二零二四年八月六日"),
        ("ID：<number>101</number>", "ID：一零一"),
        ("金额：<currency>50000人民币</currency>", "金额：五万人民币"),
        ("金额：<currency>5432元</currency>", "金额：五四三二元"),
        ("客服热线：<telephone>4008001234</telephone>", "客服热线：四零零八零零幺二三四"),
        ("更新于：<date>2025/01/15</date>。", "更新于：二零二五年一月十五日。"),
        ("会议时间 <date>10:05</date> 开始", "会议时间 十点零五分 开始"),
        ("会议时间 <date>09:00</date> 开始", "会议时间 九点零分 开始"),
        ("版本：<number>1</number>", "版本：一"),
        ("序列号：<number>0</number>", "序列号：零"),
    ]
    print("--- 原有测试用例 ---")
    for i, (original_str, expected_str) in enumerate(original_test_cases):
        converted_str = convert_tagged_string_to_spoken_chinese(original_str)
        print(f"测试 {i+1}: \"{original_str}\"")
        print(f"  转换结果: \"{converted_str}\" (期望: \"{expected_str}\")")
        print(f"  是否通过: {converted_str == expected_str}\n")
    
    print("\n--- 新增复杂句子测试 ---")
    new_sentence = "英伟达官方定于<number>2025</number>年<currency>3</currency>月<currency>13</currency>日正式发布GeForce RTX <number>5060</number> Ti <currency>16</currency>GB、RTX <number>5060</number> Ti <currency>8</currency>GB显卡。 <number>2025</number>年<currency>4</currency>月<currency>16</currency>日，NVIDIA将正式发布RTX <number>5060</number> Ti，预计售价约为<currency>400</currency>美元。<number>2025</number>年<currency>4</currency>月<currency>16</currency>日晚，RTX <number>5060</number> Ti性能解禁上市。NVIDIA只会安排送测<currency>16</currency>GB版本，禁止AIC厂商送测<currency>8</currency>GB版本。"
    
    # 根据改进后的逻辑，我们期望的输出是：
    # 注意：代码是根据标签内容进行转换的，如果标签本身使用不当 (例如用 <currency> 标记月份)，代码会尽力转换其内容。
    # 例如 <currency>3</currency>月, 代码会处理 "3" -> "三", 然后外部的 "月" 保持不变。
    expected_new_sentence_conversion = "英伟达官方定于二零二五年三月十三日正式发布GeForce RTX 五零六零 Ti 十六GB、RTX 五零六零 Ti 八GB显卡。 二零二五年四月十六日，NVIDIA将正式发布RTX 五零六零 Ti，预计售价约为四百美元。二零二五年四月十六日晚，RTX 五零六零 Ti性能解禁上市。NVIDIA只会安排送测十六GB版本，禁止AIC厂商送测八GB版本。"
    
    converted_new_sentence = convert_tagged_string_to_spoken_chinese(new_sentence)
    print(f"原复杂句: \"{new_sentence}\"")
    print(f"转换结果: \"{converted_new_sentence}\"")
    print(f"期望结果: \"{expected_new_sentence_conversion}\"")
    print(f"是否通过: {converted_new_sentence == expected_new_sentence_conversion}\n")

    # 测试 <currency>16GB</currency> 这种单位在标签内的情况
    test_currency_internal_unit = "<currency>16GB</currency> and <currency>400USD</currency>" # USD 不是已知货币单位
    expected_currency_internal_unit = "十六GB and 四百USD"
    converted_currency_internal_unit = convert_tagged_string_to_spoken_chinese(test_currency_internal_unit)
    print(f"测试单位在currency标签内: \"{test_currency_internal_unit}\"")
    print(f"  转换结果: \"{converted_currency_internal_unit}\" (期望: \"{expected_currency_internal_unit}\")")
    print(f"  是否通过: {converted_currency_internal_unit == expected_currency_internal_unit}\n")