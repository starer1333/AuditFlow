"""
阶段四：数据校验与字段映射（对应第五道关卡）
运行：python step4_validate_and_map.py
"""
import os
import json

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
DATA_FILE = os.path.join(OUTPUT_DIR, "extracted_data.json")


def luhn_check(card_num):
    """Luhn算法校验银行卡号"""
    if not card_num:
        return False
    digits = [int(c) for c in card_num if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    rev = digits[::-1]
    total = 0
    for i, d in enumerate(rev):
        if i % 2:
            d *= 2
            if d > 9: d = d // 10 + d % 10
        total += d
    return total % 10 == 0


def main():
    print("=" * 50)
    print("阶段四：数据校验与置信度评估")
    print("=" * 50)

    if not os.path.exists(DATA_FILE):
        print("❌ 找不到 extracted_data.json，请先运行阶段三")
        input("\n按回车退出...")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n原始数据:")
    print(f"  银行: {data.get('bank_name')}")
    print(f"  账号: {data.get('account_number')}")
    print(f"  余额: {data.get('ending_balance')}")
    print(f"  原始置信度: {data.get('confidence', 0) * 100:.0f}%")

    checks = []
    conf = data.get('confidence', 0)
    acc = data.get('account_number')

    # Luhn校验
    if acc and luhn_check(acc):
        print("\n✅ Luhn校验通过 - 账号格式合法")
        checks.append("Luhn通过")
    else:
        print("\n⚠️ Luhn校验失败或账号缺失 - 可能存在识别错误")
        checks.append("Luhn失败")
        conf = min(conf, 0.5)

    # 字段完整性检查
    if data.get('ending_balance') is None:
        checks.append("无余额")
        conf = min(conf, 0.4)
    if not data.get('bank_name'):
        checks.append("无银行名")
        conf = min(conf, 0.4)
    if not data.get('statement_period'):
        checks.append("无期间")

    # 跨文档勾稽（模拟，实际可扩展）
    data['validation'] = {'checks': checks, 'final_confidence': conf, 'need_human_review': conf < 0.7}
    data['mapped_fields'] = {
        'bank_name_std': data.get('bank_name'),
        'account_number_std': data.get('account_number'),
        'balance_std': data.get('ending_balance'),
        'period_std': data.get('statement_period')
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n最终置信度: {conf * 100:.0f}%")
    if conf < 0.7:
        print("⚠️ 置信度较低，建议人工复核（HITL Gateway触发）")
    else:
        print("✅ 数据质量良好，可直接采纳")
    print(f"校验备注: {', '.join(checks) if checks else '无异常'}")
    print("\n✅ 阶段四完成，可运行阶段五。")
    input("\n按回车退出...")


if __name__ == "__main__":
    main()