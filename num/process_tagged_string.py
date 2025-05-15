import re

def add_ssml_tags(text: str) -> str:
    """
    Adds SSML-like tags (<currency> or <number>) to numerical values in a string.

    - Numbers followed by specific currency keywords (人民币, 元, 美元, 美金)
      or units (度, 瓦) are tagged with <currency> around the number.
    - Other numbers (integer or decimal) are tagged with <number>.

    Args:
        text: The input string.

    Returns:
        The string with SSML-like tags added.
    """

    currency_units_keywords = ["人民币", "元", "美元", "美金", "度", "瓦", "W", "w", "%","日","月","G","GB","M","MB","T","TB"]
    num_pattern_core = r"\d+(?:\.\d+)?"
    
    # This is the regex alternation for the units, e.g., "人民币|元|..."
    # Used for direct matching within a capturing group and for negative lookahead.
    units_alternation_str = "|".join(re.escape(unit) for unit in currency_units_keywords)

    # Regex pattern:
    # G1: The number part for a currency/unit construct
    # G2: The currency/unit keyword itself
    # G3: The number part for a standalone number (asserted not to be followed by a known unit)
    pattern_str = (
        rf"({num_pattern_core})"          # G1: Number for currency/unit
        rf"({units_alternation_str})"     # G2: A specific currency unit keyword
        rf"|"                             # OR
        rf"({num_pattern_core})"          # G3: Standalone number
        rf"(?!{units_alternation_str})"   # Negative lookahead: not followed by any known unit keyword
                                          # (ensuring this number wasn't part of a currency/unit missed by the first alternative)
    )
    
    compiled_pattern = re.compile(pattern_str)

    def tagging_callback(match: re.Match) -> str:
        # Uncomment the line below to print debug information for each match found:
        # print(f"Match: group(0)='{match.group(0)}', G1='{match.group(1)}', G2='{match.group(2)}', G3='{match.group(3)}'")
        
        # Case 1: Currency/unit - G1 (number) and G2 (unit) are both present
        if match.group(1) and match.group(2):
            number_str = match.group(1)
            unit_str = match.group(2)
            return f"<currency>{number_str}</currency>{unit_str}"
        
        # Case 2: Standalone number - G3 (number) is present
        # (G1 and G2 would be None if this branch of the alternation was taken)
        elif match.group(3):
            number_str = match.group(3)
            return f"<number>{number_str}</number>"
        
        # Fallback: Should ideally not be reached if the regex logic is complete for all matches.
        # If it's reached, it means the pattern matched something, but neither of the above conditions were met,
        # which would indicate an issue with the regex group structure or callback logic.
        return match.group(0)

    return compiled_pattern.sub(tagging_callback, text)

if __name__ == '__main__':
    print("Running SSML tagging examples:")

    test_cases = [
        ("金额：50000人民币", "金额：<currency>50000</currency>人民币"),
        ("金额：5432元", "金额：<currency>5432</currency>元"),
        ("你的收入：120000美元", "你的收入：<currency>120000</currency>美元"),
        ("成本是1500美金。", "成本是<currency>1500</currency>美金。"),
        ("温度：25度，湿度：60%", "温度：<currency>25</currency>度，湿度：<currency>60</currency>%"),
        ("功率是100瓦。", "功率是<currency>100</currency>瓦。"),
        ("我有3个苹果，价格是15.5元。", "我有<number>3</number>个苹果，价格是<currency>15.5</currency>元。"),
        ("订单号888，金额123.45元，数量2件。", "订单号<number>888</number>，金额<currency>123.45</currency>元，数量<number>2</number>件。"),
        ("混合测试：100元和200美元，还有300。", "混合测试：<currency>100</currency>元和<currency>200</currency>美元，还有<number>300</number>。"),
        ("数字在词中：item123型号，code456版本，value78.9。", "数字在词中：item<number>123</number>型号，code<number>456</number>版本，value<number>78.9</number>。"),
        ("无数字字符串。", "无数字字符串。"),
        ("", ""),
        ("只有数字123 和 456.78", "只有数字<number>123</number> 和 <number>456.78</number>"),
        ("美元兑人民币汇率是6.9元。", "美元兑人民币汇率是<currency>6.9</currency>元。"), # TC14 (already correct)
        ("美元兑人民币汇率是6.9。", "美元兑人民币汇率是<number>6.9</number>。"),
        ("100度高温和20瓦功率。", "<currency>100</currency>度高温和<currency>20</currency>瓦功率。"),
        ("测试数字后直接是单位列表一部分但不是完整单位: 50美", "测试数字后直接是单位列表一部分但不是完整单位: <number>50</number>美"), # "美" is not "美金" or "美元"
        ("测试100.50元", "测试<currency>100.50</currency>元"),
        ("测试300.", "测试<number>300</number>."), # number ending with a dot
        ("5060显卡", "<number>5060</number>显卡"),
        ("5060Ti", "<number>5060</number>Ti"),
        ("1440 分辨率", "<number>1440</number> 分辨率"),
        ("70w", "<currency>70</currency>w"),
        ("英伟达官方定于2025年3月13日正式发布GeForce RTX 5060 Ti 16GB、RTX 5060 Ti 8GB显卡。 2025年4月16日，NVIDIA将正式发布RTX 5060 Ti，预计售价约为400美元。2025年4月16日晚，RTX 5060 Ti性能解禁上市。NVIDIA只会安排送测16GB版本，禁止AIC厂商送测8GB版本。", "")
    ]

    all_passed = True
    for i, (original, expected) in enumerate(test_cases):
        result = add_ssml_tags(original)
        print(f"\nTest Case {i+1}:")
        print(f"  Input:    \"{original}\"")
        print(f"  Expected: \"{expected}\"")
        print(f"  Actual:   \"{result}\"")
        if result == expected:
            print("  Status:   PASS")
        else:
            print("  Status:   FAIL ({original})") # Added original to fail message for easier identification
            all_passed = False
    
    if all_passed:
        print("\nAll test cases passed!")
    else:
        print("\nSome test cases failed.")