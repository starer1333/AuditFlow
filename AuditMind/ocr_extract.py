"""
阶段三：OCR识别与字段提取（对应第三、四道关卡）
运行：python step3_ocr_extract.py
"""
import os
import re
import json
from paddleocr import PaddleOCR

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
CLEANED_IMG = os.path.join(OUTPUT_DIR, "cleaned_image.png")


def extract_fields(text):
    """
    语义抽取与字段映射
    支持中英文混杂、复杂汉字、多种表述
    """
    data = {"bank_name": None, "account_number": None, "ending_balance": None,
            "statement_period": None, "confidence": 0.0}
    if not text:
        return data

    # 银行名称（支持中文全称、简称、英文缩写）
    patterns = [
        r"(中国[a-zA-Z]*银行)",
        r"([a-zA-Z]*银行.*?支行)",
        r"(工商银行|农业银行|中国银行|建设银行|交通银行|招商银行|中信银行|光大银行|民生银行|兴业银行|平安银行|浦发银行|华夏银行|广发银行|邮储银行)",
        r"(ICBC|BOC|CCB|ABC|CMB|CIB|SPDB|CEB|CMBC|PINGAN)"
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            data["bank_name"] = m.group(1)
            data["confidence"] += 0.25
            break

    # 账号（支持中文"账号"、英文"Account/A/C"等多种表述）
    m = re.search(r"(?:账号|帐户|账户|Account|A/C)[:\s]*(\d{12,19})", text, re.I)
    if not m:
        m = re.search(r"\b(\d{16,19})\b", text)
    if m:
        data["account_number"] = m.group(1)
        data["confidence"] += 0.25

    # 余额（支持¥/$符号、千分位逗号）
    m = re.search(r"(?:余额|Balance|期末余额)[:\s]*[¥$]?\s*([\d,]+\.?\d*)", text, re.I)
    if m:
        try:
            data["ending_balance"] = float(m.group(1).replace(",", ""))
            data["confidence"] += 0.25
        except:
            pass

    # 期间（支持多种日期格式）
    m = re.search(
        r"(?:期间|Period|对账期间)[:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?(?:\s*[-~至]\s*\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)?)",
        text)
    if m:
        data["statement_period"] = m.group(1)
        data["confidence"] += 0.25

    data["raw_text_sample"] = text[:500]
    return data


def main():
    print("=" * 50)
    print("阶段三：OCR识别与字段提取")
    print("=" * 50)

    if not os.path.exists(CLEANED_IMG):
        print(f"❌ 找不到净化图片: {CLEANED_IMG}")
        print("   请先运行阶段二: python step2_format_and_clean.py")
        input("\n按回车退出...")
        return

    print("正在初始化PaddleOCR（首次运行下载模型，支持中英文及复杂汉字）...")
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    print("✅ OCR引擎就绪")

    print("\n正在进行OCR识别（处理水印、印章、倾斜干扰后的图片）...")
    result = ocr.ocr(CLEANED_IMG, cls=True)

    if not result or not result[0]:
        print("❌ OCR未识别到任何文字")
        return

    text_lines = [line[1][0] for line in result[0] if line]
    full_text = "\n".join(text_lines)
    print(f"✅ 识别到 {len(full_text)} 个字符")

    print("\n正在提取关键字段...")
    data = extract_fields(full_text)

    print("\n" + "=" * 40)
    print("提取结果:")
    print(f"  银行名称: {data['bank_name'] or '未识别'}")
    print(f"  银行账号: {data['account_number'] or '未识别'}")
    print(f"  期末余额: {data['ending_balance'] or '未识别'}")
    print(f"  对账期间: {data['statement_period'] or '未识别'}")
    print(f"  置信度: {data['confidence'] * 100:.0f}%")
    print("=" * 40)

    json_path = os.path.join(OUTPUT_DIR, "extracted_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已保存至: {json_path}")
    print("\n✅ 阶段三完成，可运行阶段四。")
    input("\n按回车退出...")


if __name__ == "__main__":
    main()