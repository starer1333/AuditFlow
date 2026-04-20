def luhn_check(card):
    if not card: return False
    d = [int(c) for c in card if c.isdigit()]
    if len(d)<13 or len(d)>19: return False
    rev = d[::-1]
    total = 0
    for i, v in enumerate(rev):
        if i%2:
            v *= 2
            if v>9: v = v//10 + v%10
        total += v
    return total%10 == 0

def validate(data):
    conf = data.get("confidence", 0)
    acc = data.get("account_number")
    checks = []
    if acc and luhn_check(acc): checks.append("Luhn通过")
    else: checks.append("Luhn失败"); conf = min(conf, 0.5)
    if not data.get("ending_balance"): checks.append("无余额"); conf = min(conf, 0.4)
    if not data.get("bank_name"): checks.append("无银行名"); conf = min(conf, 0.4)
    data["validation"] = {"checks": checks, "final_confidence": conf, "need_review": conf<0.7}
    return data