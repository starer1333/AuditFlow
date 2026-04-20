import re
from paddleocr import PaddleOCR

RARE_RANGES = [(0x3400,0x4DBF),(0x20000,0x2A6DF),(0x2A700,0x2B73F),(0x2B740,0x2B81F),(0x2B820,0x2CEAF),(0x2CEB0,0x2EBEF)]
CORR_DICT = {"很行":"银行","支竹":"支付","共应":"供应","人账":"入账","己收":"已收","末收":"未收"}
BANK_MAP = {"ICBC":"中国工商银行","BOC":"中国银行","CCB":"中国建设银行","ABC":"中国农业银行","CMB":"招商银行"}

def detect_rare_chinese(text):
    rare = []
    total = 0
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            total += 1
        elif any(s<=ord(c)<=e for s,e in RARE_RANGES):
            rare.append(c)
            total += 1
    return {"has": len(rare)>0, "count": len(rare), "samples": list(set(rare))[:10]}

def detect_mixed(text):
    cn = re.findall(r'[\u4e00-\u9fff]', text)
    en = re.findall(r'[a-zA-Z]', text)
    mixed = [l[:50] for l in text.split('\n') if re.search(r'[\u4e00-\u9fff]', l) and re.search(r'[a-zA-Z]', l)]
    return {"has": bool(cn and en), "count": len(mixed)}

def correct_errors(text):
    for w, r in CORR_DICT.items():
        text = text.replace(w, r)
    return text

def extract_fields(text):
    d = {"bank_name":None,"account_number":None,"ending_balance":None,"period":None,"confidence":0.0}
    for p in [r"(中国[a-zA-Z]*银行)", r"([a-zA-Z]*银行.*?支行)", r"(工商|农业|中国|建设|交通|招商)银行", r"(ICBC|BOC|CCB|ABC|CMB)"]:
        m = re.search(p, text, re.I)
        if m:
            d["bank_name"] = BANK_MAP.get(m.group(1).upper(), m.group(1))
            d["confidence"] += 0.25
            break
    m = re.search(r"(?:账号|账户|Account)[:\s]*(\d{12,19})", text, re.I) or re.search(r"\b(\d{16,19})\b", text)
    if m: d["account_number"], d["confidence"] = m.group(1), d["confidence"]+0.25
    m = re.search(r"(?:余额|Balance)[:\s]*[¥$]?\s*([\d,]+\.?\d*)", text, re.I)
    if m:
        try: d["ending_balance"], d["confidence"] = float(m.group(1).replace(",","")), d["confidence"]+0.25
        except: pass
    m = re.search(r"(?:期间|Period)[:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)", text)
    if m: d["period"], d["confidence"] = m.group(1), d["confidence"]+0.25
    return d

def ocr_image(img_path):
    ocr = PaddleOCR(lang="ch")
    res = ocr.ocr(img_path)
    if not res or not res[0]: return "", {}
    text = "\n".join([l[1][0] for l in res[0] if l])
    rare = detect_rare_chinese(text)
    if rare["has"]: text = correct_errors(text)
    mixed = detect_mixed(text)
    fields = extract_fields(text)
    fields["rare_info"] = rare
    fields["mixed_info"] = mixed
    return text, fields