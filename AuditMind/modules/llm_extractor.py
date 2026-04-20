import requests
import base64
import json
import re
from config import SILICONFLOW_API_KEY, LLM_MODEL

def call_llm(image_path, prompt):
    if not SILICONFLOW_API_KEY or SILICONFLOW_API_KEY == "sk-your-api-key-here":
        return None
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
        ]}],
        "temperature": 0.1
    }
    r = requests.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload, timeout=60)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return None

def extract_with_llm(image_path, ocr_fields):
    prompt = f"""
你是审计专家。OCR已提取如下信息：{json.dumps(ocr_fields, ensure_ascii=False)}
请仔细观察图片，完成：
1. 修正OCR错误（特别注意水印遮挡、生僻字、中英文混排）。
2. 提取以下字段，返回JSON：
{{"bank_name":"","account_number":"","ending_balance":数字,"period":"","currency":"","confidence":0.0,"risk_notes":"简要风险意见"}}
只返回JSON。
"""
    resp = call_llm(image_path, prompt)
    if resp:
        m = re.search(r'\{.*\}', resp, re.DOTALL)
        if m:
            try: return json.loads(m.group())
            except: pass
    return None

def fuse_results(ocr, llm):
    if not llm: return ocr
    fused = {
        "bank_name": llm.get("bank_name") or ocr.get("bank_name"),
        "account_number": llm.get("account_number") or ocr.get("account_number"),
        "ending_balance": llm.get("ending_balance") or ocr.get("ending_balance"),
        "period": llm.get("period") or ocr.get("period"),
        "currency": llm.get("currency", "RMB"),
        "confidence": max(ocr.get("confidence",0), llm.get("confidence",0)),
        "risk_notes": llm.get("risk_notes", ""),
        "ocr_raw": ocr,
        "llm_raw": llm
    }
    return fused