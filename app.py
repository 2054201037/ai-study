"""简单的天气查询模拟器。

用户输入城市名称，程序随机生成当天的天气、温度，
并根据温度和天气状况给出一条出门穿衣建议。
仅使用 Python 标准库，无需安装任何第三方依赖。
"""

import random

# 可能出现的天气状况
WEATHER_CONDITIONS = [
    "晴", "多云", "阴", "小雨", "中雨",
    "雷阵雨", "小雪", "雾", "大风",
]

# 温度区间 -> 穿衣主建议（按从冷到热排列）
TEMP_ADVICE = [
    (-100, 0, "天气寒冷，建议穿厚羽绒服、棉衣，戴好围巾、手套和帽子"),
    (0, 10, "气温偏低，建议穿大衣、厚外套搭配毛衣，注意保暖"),
    (10, 18, "天气凉爽，建议穿夹克、风衣或薄毛衣，早晚可加件外套"),
    (18, 25, "温度舒适，建议穿长袖衬衫、薄外套或卫衣"),
    (25, 32, "天气较热，建议穿短袖、短裤或薄裙等透气衣物"),
    (32, 100, "高温炎热，建议穿轻薄透气的夏装，尽量避开正午外出"),
]

# 特殊天气 -> 附加建议
WEATHER_EXTRA_ADVICE = {
    "小雨": "记得带伞，路面湿滑请慢行",
    "中雨": "请携带雨伞，最好穿防水鞋",
    "雷阵雨": "尽量减少外出，远离大树和高处，注意防雷",
    "小雪": "注意防滑保暖，穿防滑鞋",
    "雾": "能见度低，外出注意交通安全，可戴上口罩",
    "大风": "风大注意防风，别穿太宽松易被吹起的衣物",
}


def generate_weather():
    """随机生成天气状况和温度（温度范围 -5 ~ 38 摄氏度）。"""
    weather = random.choice(WEATHER_CONDITIONS)
    temperature = random.randint(-5, 38)
    return weather, temperature


def get_clothing_advice(temperature, weather):
    """根据温度和天气状况生成穿衣建议。"""
    for low, high, advice in TEMP_ADVICE:
        if low <= temperature < high:
            main_advice = advice
            break

    extra = WEATHER_EXTRA_ADVICE.get(weather)
    if extra:
        return f"{main_advice}；{extra}"
    return main_advice


def print_weather_report(city, weather, temperature, advice):
    """以友好的格式打印天气报告。"""
    line = "=" * 40
    print()
    print(line)
    print(f"  {city} 今日天气")
    print(line)
    print(f"  天气状况：{weather}")
    print(f"  当前温度：{temperature} ℃")
    print(f"  穿衣建议：{advice}")
    print(line)
    print()


def main():
    print("欢迎使用天气查询模拟器！")
    print("输入城市名称即可查询天气，输入 q 或直接回车退出。")

    while True:
        city = input("请输入城市名称：").strip()
        if not city or city.lower() == "q":
            print("再见，祝您每天都有好心情！")
            break

        weather, temperature = generate_weather()
        advice = get_clothing_advice(temperature, weather)
        print_weather_report(city, weather, temperature, advice)


if __name__ == "__main__":



    main()
