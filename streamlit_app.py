 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/streamlit_app.py b/streamlit_app.py
index 8cdaccbbfcb31d4632bf575bd3a5b1e8355f1d5a..239cce340a027bcec1c12f8ae7019edf23abbf88 100644
--- a/streamlit_app.py
+++ b/streamlit_app.py
@@ -1,78 +1,82 @@
 """
 AuditFlow — 审计数据中枢（完整功能版）
 五大痛点 · 六类文档 · 双模型驱动 · 智能底稿生成 · 账号 Luhn + BIN 校验
 德勤数字化精英挑战赛 Team J
 """
 
 import streamlit as st
 import requests
 import base64
 import json
 import io
 import re
 import os
 import tempfile
 import csv
+import importlib
+import importlib.util
 from datetime import datetime
 import openpyxl
 from openpyxl.styles import Font, Alignment, PatternFill
 
 # ==================== BIN 数据库加载 ====================
 @st.cache_data
 def load_bin_database():
     """加载卡BIN数据库，返回 {bin_prefix: bank_name} 字典"""
     bin_dict = {}
     bin_csv_path = os.path.join(os.path.dirname(__file__), "binlist.csv")
     if os.path.exists(bin_csv_path):
         try:
             with open(bin_csv_path, "r", encoding="utf-8") as f:
                 reader = csv.DictReader(f)
                 for row in reader:
                     bin_code = row.get("bin", "").strip()
                     bank_name = row.get("bank", "").strip()
                     if bin_code and bank_name:
                         bin_dict[bin_code] = bank_name
         except:
             pass
     if not bin_dict:
         bin_dict = {
             "622848": "中国农业银行",
             "622200": "中国工商银行",
             "621700": "中国建设银行",
             "621660": "中国银行",
             "622260": "交通银行",
             "621485": "招商银行",
             "622588": "招商银行",
             "621771": "中国邮政储蓄银行",
             "622521": "中国邮政储蓄银行",
             "622180": "中国邮政储蓄银行",
             "622821": "中国邮政储蓄银行",
         }
     return bin_dict
 
 BIN_DATABASE = load_bin_database()
+SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
+SILICONFLOW_MODEL = "Qwen/Qwen2-VL-72B-Instruct"
 
 def luhn_check(card_num: str) -> bool:
     """Luhn算法校验银行卡号有效性"""
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
             if d > 9:
                 d = d // 10 + d % 10
         total += d
     return total % 10 == 0
 
 def get_bank_by_bin(account_number: str) -> str:
     """根据账号前6位BIN码查询发卡行"""
     if not account_number:
         return None
     clean = ''.join(c for c in account_number if c.isdigit())
     if len(clean) < 6:
         return None
@@ -127,50 +131,94 @@ def parse_deepseek_ocr_response(raw_response: str) -> str:
     parsed_parts = []
     if tables:
         for table in tables:
             clean_table = table.strip()
             parsed_parts.append("[表格内容]")
             parsed_parts.append(clean_table)
     text_pattern = r'<\|ref\|>text<\|/ref\|><\|det\|>\[[^\]]*\]<\|/det\|>\s*([^<]+)'
     texts = re.findall(text_pattern, raw_response, re.DOTALL)
     for text in texts:
         clean_text = text.strip()
         if clean_text and not clean_text.startswith('<'):
             parsed_parts.append(clean_text)
     if not parsed_parts:
         clean = re.sub(r'<\|[^|]+\|>', ' ', raw_response)
         clean = re.sub(r'\[\[[^\]]+\]\]', ' ', clean)
         clean = re.sub(r'<[^>]+>', ' ', clean)
         clean = re.sub(r'\s+', ' ', clean).strip()
         return clean[:2000] if clean else raw_response[:500]
     result = "\n".join(parsed_parts)
     result = re.sub(r'<\|[^|]+\|>', '', result)
     result = re.sub(r'\[\[[^\]]+\]\]', '', result)
     result = re.sub(r'<[^>]+>', '', result)
     result = re.sub(r'\n\s*\n', '\n', result)
     return result.strip() or raw_response[:500]
 
+def call_siliconflow_chat(api_key: str, model: str, messages: list, temperature=0.1, max_tokens=2048, timeout=60):
+    """统一调用 SiliconFlow 聊天接口，返回 (success, content)。"""
+    if not api_key:
+        return False, ""
+    headers = {"Authorization": f"Bearer {api_key}"}
+    payload = {
+        "model": model,
+        "messages": messages,
+        "temperature": temperature,
+        "max_tokens": max_tokens
+    }
+    try:
+        resp = requests.post(SILICONFLOW_API_URL, headers=headers, json=payload, timeout=timeout)
+        if resp.status_code == 200:
+            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
+            return bool(content), content or ""
+    except requests.RequestException:
+        pass
+    return False, ""
+
+def get_local_ocr_text(temp_input_path: str) -> str:
+    """
+    尝试使用本地 PaddleOCR（如环境已安装）进行识别。
+    说明：不对 import 使用 try/except；通过 find_spec 判断模块可用性。
+    """
+    if not temp_input_path:
+        return ""
+    if importlib.util.find_spec("paddleocr") is None:
+        return ""
+    paddleocr_module = importlib.import_module("paddleocr")
+    PaddleOCR = getattr(paddleocr_module, "PaddleOCR", None)
+    if PaddleOCR is None:
+        return ""
+    ocr = PaddleOCR(use_angle_cls=True, lang="ch")
+    result = ocr.ocr(temp_input_path, cls=True)
+    lines = []
+    for block in result or []:
+        for item in block or []:
+            if len(item) >= 2 and item[1]:
+                text = item[1][0]
+                if text:
+                    lines.append(str(text))
+    return "\n".join(lines).strip()
+
 def validate_file_type_and_content(llm_response, selected_type):
     """校验文件类型与财务相关性"""
     type_keywords = {
         "🏦 银行对账单": ["银行对账单", "Bank Statement", "交易明细", "借方", "贷方", "余额", "期初", "期末"],
         "📋 开户清单": ["已开立银行结算账户清单", "中国人民银行", "账户性质", "开户日期"],
         "❌ 销户清单/销户证明": ["销户", "账户关闭", "销户证明", "注销"],
         "📊 企业信用报告": ["信用报告", "信贷记录", "征信中心", "贷款", "担保"],
         "📬 银行询证函（回函）": ["银行询证函", "函证", "回函", "1-14项"],
         "⚖️ 银行存款余额调节表": ["余额调节表", "未达账项", "调节后余额", "企业账面"]
     }
     finance_keywords = ["银行", "余额", "交易", "账户", "存款", "贷款", "信用", "担保", "函证", "对账", "金额", "人民币", "USD", "RMB", "HSBC", "Balance", "Statement"]
     content_lower = llm_response.lower()
     expected_keywords = type_keywords.get(selected_type, [])
     type_match = any(kw.lower() in content_lower for kw in expected_keywords)
     is_finance = any(kw.lower() in content_lower for kw in finance_keywords)
     return {
         "type_match": type_match,
         "is_finance": is_finance,
         "warning": None if type_match else f"您上传的文件内容与所选类型（{selected_type}）不一致",
         "error": None if is_finance else "上传的文件并非财务相关文件，请上传银行对账单等审计资料"
     }
 
 def generate_excel_by_type(data, file_type, company="XX科技有限公司"):
     """根据文件类型生成对应Excel底稿"""
     wb = openpyxl.Workbook()
@@ -420,248 +468,255 @@ with col1:
     <table class="comparison-table">
         <tr><th>对比维度</th><th>传统审计模式</th><th>市面AI工具</th><th><span style="color:#68d391">AuditFlow</span></th></tr>
         <tr><td>数据整合</td><td>手工跨系统导出、清洗</td><td>单一工具处理特定格式</td><td class="highlight">多格式智能整合，会计学规则映射</td></tr>
         <tr><td>风险识别</td><td>依赖抽样，漏检率高</td><td>通用模型，解释性差</td><td class="highlight">基于审计准则的规则引擎，可解释性强</td></tr>
         <tr><td>人机协同</td><td>完全人工</td><td>AI替代，关键判断缺失</td><td class="highlight">AI辅助+人工复核，保留专业判断</td></tr>
         <tr><td>效率提升</td><td>有限，耗时长</td><td>局部效率提升</td><td class="highlight">综合效率提升70%+，风险识别率提高15%</td></tr>
     </table>
     """, unsafe_allow_html=True)
 with col2:
     st.markdown("### 🧠 理论支撑")
     st.markdown("""<div class="theory-box"><p class="theory-label">德勤研究指出：</p><p class="theory-quote">“AI将重构审计作业流程，从<span class="theory-highlight">经验驱动</span>转向<span class="theory-highlight">智能驱动</span>。”</p><p class="theory-label" style="margin-top:1rem;">Jeffrey导师强调：</p><p class="theory-quote">“审计数字化大脑需具备<span class="theory-highlight">感知、认知、决策、协同</span>四大能力，实现从<span class="theory-highlight">单点工具</span>到<span class="theory-highlight">统一智能层</span>的跃迁。”</p><p style="margin-top:1rem; color: #68d391;">✅ AuditFlow正是这一理念的完美实践。</p></div>""", unsafe_allow_html=True)
 
 st.divider()
 
 # -------------------- 文件上传区 --------------------
 st.markdown("### 📁 上传银行源文件")
 col1, col2 = st.columns([1, 2])
 with col1:
     file_type = st.selectbox("📋 文件类型", options=["🏦 银行对账单", "📋 开户清单", "❌ 销户清单/销户证明", "📊 企业信用报告", "📬 银行询证函（回函）", "⚖️ 银行存款余额调节表"], index=0)
 with col2:
     uploaded_file = st.file_uploader("拖拽文件或点击浏览", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed")
     st.caption("支持 PDF、PNG、JPG 格式")
 
 # -------------------- API 配置 --------------------
 SILICONFLOW_API_KEY = st.secrets.get("SILICONFLOW_API_KEY", "")
-SILICONFLOW_MODEL = "Qwen/Qwen2-VL-72B-Instruct"
 
 # -------------------- 审计意见参考库 --------------------
 with st.expander("📝 审计意见参考库（可编辑）", expanded=True):
     default_reference = """其他确认与计量问题
 （一）未恰当核算定制化产品相关研发支出
 根据企业会计准则及相关规定，企业为履行合同发生的成本，不属于其他企业会计准则规范范围且同时满足相关条件的，应当作为合同履约成本确认为一项资产，采用与该资产相关的商品的收入确认基础进行摊销，计入当期损益。
 
 （二）未正确处理固定资产修复支出
 根据企业会计准则及相关规定，固定资产的后续支出是指固定资产在使用过程中发生的更新改造支出、修理费用等支出。对于固定资产的后续支出，符合固定资产确认条件的，应当计入固定资产成本，同时扣除被替换部分的账面价值；不符合固定资产确认条件的，应当在发生时计入当期损益。
 
 （三）未恰当确认和计量在建工程
 根据企业会计准则及相关规定，企业以出包方式建造固定资产，其成本由建造该项固定资产达到预定可使用状态前所发生的必要支出构成，包括发生的建筑工程支出、安装工程支出以及需分摊计入固定资产价值的待摊支出。
 
 （四）未正确处理解除租赁所支付的违约金
 根据企业会计准则及相关规定，租赁变更导致租赁范围缩小或租赁期缩短的，承租人应当相应调减使用权资产的账面价值，并将相关利得或损失计入资产处置损益。
 
 （五）未恰当处理转让子公司股权形成的预计负债
 若一项义务同时满足是企业承担的现时义务、履行该义务很可能导致经济利益流出企业、该义务的金额能够可靠地计量，则应当确认为预计负债。
 
 （六）未恰当核算股份支付相关递延所得税
 对于附有业绩条件或服务条件的股权激励计划，企业按照会计准则确认的成本费用在等待期不得税前抵扣，待股权激励计划行权时方可抵扣。
 
 （七）未正确区分会计估计变更与前期差错更正
 会计估计变更是指由于资产和负债的当前状况及预期经济利益和义务发生了变化而对资产或负债账面价值进行的调整；前期差错是指由于没有运用或错误运用可靠信息而对前期财务报表造成的省略或错报。"""
     audit_opinion_reference = st.text_area("参考范例", value=default_reference, height=200)
 
 if uploaded_file:
     st.success(f"✅ 已上传：{uploaded_file.name}")
     if uploaded_file.type.startswith("image"):
         st.image(uploaded_file, width=400)
 
     if st.button("🚀 开始智能处理", type="primary", use_container_width=True):
-        with st.spinner("⏳ 正在提取文本..."):
-            suffix = os.path.splitext(uploaded_file.name)[1]
-            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
-                tmp.write(uploaded_file.getvalue())
-                temp_input_path = tmp.name
-
-            ocr_text = ""
-            ocr_api_success = False
-            try:
+        ocr_api_success = False
+        ocr_local_success = False
+        temp_input_path = ""
+        try:
+            with st.spinner("⏳ 正在提取文本..."):
+                suffix = os.path.splitext(uploaded_file.name)[1]
+                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
+                    tmp.write(uploaded_file.getvalue())
+                    temp_input_path = tmp.name
+
+                ocr_text = ""
                 img_bytes = uploaded_file.getvalue()
                 img_b64 = base64.b64encode(img_bytes).decode()
-                headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
-                payload = {
-                    "model": "deepseek-ai/DeepSeek-OCR",
-                    "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}, {"type": "text", "text": "<image>\n<|grounding|>Convert the document to markdown."}]}],
-                    "temperature": 0.1, "max_tokens": 2048
-                }
-                resp = requests.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload, timeout=60)
-                if resp.status_code == 200:
-                    ocr_text = resp.json()["choices"][0]["message"]["content"]
-                    ocr_api_success = True
-            except:
-                ocr_text = ""
-
-            if not ocr_text:
-                ocr_text = """中国工商银行北京朝阳支行\n账号：6222020200123456789\n币种：RMB\n对账单期间：2025-12-01 至 2025-12-31\n期末余额：1,250,000.00"""
-                st.info("📌 云端OCR暂不可用，当前为模拟演示模式。")
-
-            parsed_ocr_text = parse_deepseek_ocr_response(ocr_text)
-            st.markdown("### 🔍 识别的原始文本")
-            st.text_area("提取的文本", parsed_ocr_text, height=200)
-
-        with st.spinner("🤖 正在调用大模型分析..."):
-            prompt = f"""你是一名资深注册会计师。请根据以下OCR文本完成专业判断。\n**文件类型**：{file_type}\n**OCR内容**：\n{parsed_ocr_text[:3000]}\n\n1. 内容识别与分类\n2. 关键数据提取（JSON格式）\n3. 数据质量评估（置信度0.0-1.0）\n4. 审计意见草稿\n5. 风险提示\n\n参考范例：{audit_opinion_reference}\n\n最后输出JSON包含risk_notes字段。"""
-            headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
-            payload = {"model": SILICONFLOW_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 2048}
-            llm_api_success = False
-            try:
-                resp = requests.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload, timeout=60)
-                if resp.status_code == 200:
-                    llm_response = resp.json()["choices"][0]["message"]["content"]
-                    llm_api_success = True
-                else:
-                    raise Exception()
-            except:
-                llm_response = f"""1. 内容识别与分类：该文件为银行对账单，与所选类型一致。\n3. 数据质量评估：综合置信度0.95。\n4. 审计意见草稿：基于已执行的审计程序，我们认为，上述银行余额调节表在所有重大方面公允反映了银行存款余额。未发现重大异常。\n5. 风险提示：建议对期末大额余额执行函证程序。\n{{"bank_name": "中国工商银行北京朝阳支行", "account_number": "6222020200123456789", "ending_balance": 1250000.00, "statement_period": "2025-12-01至2025-12-31", "currency": "RMB", "confidence": 0.95, "risk_notes": "基于已执行的程序，未发现重大异常，银行存款余额可确认。"}}"""
-                st.info("📌 大模型API暂不可用，当前为模拟演示模式。")
+                ocr_messages = [{
+                    "role": "user",
+                    "content": [
+                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
+                        {"type": "text", "text": "<image>\n<|grounding|>Convert the document to markdown."}
+                    ]
+                }]
+                ocr_api_success, ocr_text = call_siliconflow_chat(
+                    api_key=SILICONFLOW_API_KEY,
+                    model="deepseek-ai/DeepSeek-OCR",
+                    messages=ocr_messages
+                )
+
+                if not ocr_text:
+                    ocr_text = get_local_ocr_text(temp_input_path)
+                    ocr_local_success = bool(ocr_text)
+
+                if not ocr_text:
+                    ocr_text = """中国工商银行北京朝阳支行\n账号：6222020200123456789\n币种：RMB\n对账单期间：2025-12-01 至 2025-12-31\n期末余额：1,250,000.00"""
+                    st.info("📌 云端OCR与本地OCR暂不可用，当前为模拟演示模式。")
+
+                parsed_ocr_text = parse_deepseek_ocr_response(ocr_text)
+                st.markdown("### 🔍 识别的原始文本")
+                st.text_area("提取的文本", parsed_ocr_text, height=200)
+
+            with st.spinner("🤖 正在调用大模型分析..."):
+                prompt = f"""你是一名资深注册会计师。请根据以下OCR文本完成专业判断。\n**文件类型**：{file_type}\n**OCR内容**：\n{parsed_ocr_text[:3000]}\n\n1. 内容识别与分类\n2. 关键数据提取（JSON格式）\n3. 数据质量评估（置信度0.0-1.0）\n4. 审计意见草稿\n5. 风险提示\n\n参考范例：{audit_opinion_reference}\n\n最后输出JSON包含risk_notes字段。"""
+                llm_api_success, llm_response = call_siliconflow_chat(
+                    api_key=SILICONFLOW_API_KEY,
+                    model=SILICONFLOW_MODEL,
+                    messages=[{"role": "user", "content": prompt}]
+                )
+                if not llm_response:
+                    llm_response = f"""1. 内容识别与分类：该文件为银行对账单，与所选类型一致。\n3. 数据质量评估：综合置信度0.95。\n4. 审计意见草稿：基于已执行的审计程序，我们认为，上述银行余额调节表在所有重大方面公允反映了银行存款余额。未发现重大异常。\n5. 风险提示：建议对期末大额余额执行函证程序。\n{{"bank_name": "中国工商银行北京朝阳支行", "account_number": "6222020200123456789", "ending_balance": 1250000.00, "statement_period": "2025-12-01至2025-12-31", "currency": "RMB", "confidence": 0.95, "risk_notes": "基于已执行的程序，未发现重大异常，银行存款余额可确认。"}}"""
+                    st.info("📌 大模型API暂不可用，当前为模拟演示模式。")
 
             json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
             extracted = {}
             if json_match:
                 try:
                     extracted = json.loads(json_match.group())
                 except:
                     extracted = {"bank_name": "解析失败"}
 
             def get_field(data, *keys):
                 for k in keys:
                     if k in data and data[k] is not None:
                         return data[k]
                 return None
 
             bank_name = get_field(extracted, "bank_name", "bank", "银行名称", "BankName", "bankName")
             account_number = get_field(extracted, "account_number", "account", "账号", "AccountNumber", "accountNumber")
             ending_balance = get_field(extracted, "ending_balance", "balance", "期末余额", "EndingBalance", "closing_balance", "ClosingBalance")
             statement_period = get_field(extracted, "statement_period", "period", "期间", "对账期间", "StatementPeriod")
             currency = get_field(extracted, "currency", "币种", "Currency", "Cur")
             confidence = get_field(extracted, "confidence", "置信度", "Confidence")
             risk_notes = get_field(extracted, "risk_notes", "riskNotes", "审计意见", "opinion", "risk_opinion")
 
             # 余额清洗与安全转换
             if ending_balance is not None:
                 if isinstance(ending_balance, str):
                     ending_balance = re.sub(r'[£$¥€,\s]', '', ending_balance)
                     try:
                         ending_balance = float(ending_balance)
                     except:
                         ending_balance = None
                 elif not isinstance(ending_balance, (int, float)):
                     ending_balance = None
-            # 如果最终还是 None，则设为 0 供显示
-            display_balance = ending_balance if isinstance(ending_balance, (int, float)) else 0
-
             # 置信度处理
             if confidence is None:
                 confidence = 0.5
             elif isinstance(confidence, str):
                 try:
                     confidence = float(confidence.strip('%')) / 100 if '%' in confidence else float(confidence)
                 except:
                     confidence = 0.5
             confidence = max(0.0, min(1.0, confidence))
 
             # ========== 账号 Luhn + BIN 校验 ==========
             account_validation = validate_account(account_number, bank_name)
             if account_validation["message"]:
                 if account_validation["luhn_valid"] and account_validation["bank_match"]:
                     st.success(f"✅ {account_validation['message']}")
                 else:
                     st.warning(f"⚠️ {account_validation['message']}")
             confidence = confidence * account_validation["confidence_factor"]
             # ========================================
 
             # 兜底审计意见
             if not risk_notes:
                 if ending_balance is not None:
                     if ending_balance < 0:
                         risk_notes = "期末余额为负数，存在透支或异常交易风险，建议进一步核实。"
                     else:
                         risk_notes = "基于已执行的程序，未发现重大异常，银行存款余额可确认。"
                 else:
                     risk_notes = "未能提取到期末余额，请人工复核原始文件。"
 
             extracted = {
                 "bank_name": bank_name,
                 "account_number": account_number,
                 "ending_balance": ending_balance,
                 "statement_period": statement_period,
                 "currency": currency or "未识别",
                 "confidence": confidence,
                 "risk_notes": risk_notes
             }
 
             text_analysis = llm_response[:llm_response.find('{')] if '{' in llm_response else llm_response
             validation = validate_file_type_and_content(parsed_ocr_text, file_type)
             if validation["error"]:
                 st.warning(validation["error"])
             if validation["warning"]:
                 st.warning(validation["warning"])
 
             # ========== API 调用状态提示 ==========
             if ocr_api_success and llm_api_success:
                 st.success("✅ 当前使用：真实 DeepSeek-OCR + 真实大模型分析")
+            elif ocr_local_success and llm_api_success:
+                st.success("✅ 当前使用：本地 PaddleOCR + 真实大模型分析")
             elif ocr_api_success and not llm_api_success:
                 st.warning("⚠️ DeepSeek-OCR 真实调用成功，大模型使用模拟数据")
+            elif ocr_local_success and not llm_api_success:
+                st.warning("⚠️ 本地 PaddleOCR 调用成功，大模型使用模拟数据")
             elif not ocr_api_success and llm_api_success:
                 st.warning("⚠️ OCR 使用模拟数据，大模型真实调用成功")
             else:
                 st.info("📌 当前为模拟演示模式，展示完整流程")
 
             st.markdown("---")
             st.markdown("### 🤖 大模型分析报告")
             with st.expander("📋 查看详细分析", expanded=True):
                 st.markdown(text_analysis)
 
             st.markdown("### 📊 提取的关键字段")
             c1, c2, c3, c4 = st.columns(4)
             with c1: st.metric("🏦 银行名称", extracted.get("bank_name", "未识别"))
             with c2: st.metric("💳 账号", extracted.get("account_number", "未识别"))
             with c3: 
                 bal = extracted.get("ending_balance")
                 if isinstance(bal, (int, float)):
                     st.metric("💰 期末余额", f"¥ {bal:,.2f}")
                 else:
                     st.metric("💰 期末余额", "未识别")
             with c4: st.metric("📈 置信度", f"{extracted.get('confidence', 0)*100:.0f}%")
 
             if extracted.get("risk_notes"):
                 st.markdown("### 📋 审计意见")
                 st.info(extracted["risk_notes"])
 
             st.markdown("### 📥 下载审计底稿")
             excel_bytes = generate_excel_by_type(extracted, file_type)
             st.download_button(label="📊 下载 Excel 底稿", data=excel_bytes, file_name=f"审计底稿_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
             st.download_button(label="📄 下载完整报告 (JSON)", data=json.dumps({"analysis": text_analysis, "extracted": extracted}, ensure_ascii=False, indent=2), file_name=f"AuditFlow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json", use_container_width=True)
+        finally:
+            if temp_input_path and os.path.exists(temp_input_path):
+                try:
+                    os.remove(temp_input_path)
+                except OSError:
+                    pass
 
 # -------------------- 未来展望 --------------------
 with st.expander("🚀 未来展望：从单文件识别到跨文档智能审计", expanded=True):
     st.markdown("""<div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 1.5rem; border: 1px solid #334155;"><p style="color: #cbd5e1;">当前版本已实现<span style="color: #2dd4bf;">单份源文件的智能识别与底稿生成</span>。下一阶段将迈向批量上传、交叉比对、差异定位与可视化对证，成为审计师的<span style="color: #2dd4bf;">“全局风险雷达”</span>。</p></div>""", unsafe_allow_html=True)
 
 # -------------------- 数据安全与隐私保护 --------------------
 with st.expander("🔒 数据安全与隐私保护", expanded=True):
     st.markdown("""
     <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 1.5rem; border: 1px solid #334155;">
         <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.6;">
             AuditFlow 将数据安全置于首位，为企业提供<span style="color: #2dd4bf;">私有化部署</span>与<span style="color: #2dd4bf;">内网隔离</span>方案：
         </p>
         <ul style="color: #94a3b8; margin-top: 1rem; line-height: 1.8;">
             <li><span style="color: #fbbf24;">🏢 内网部署</span> — 系统可完全部署在企业内部服务器或办公电脑，无需连接外网，杜绝数据外泄风险。</li>
             <li><span style="color: #fbbf24;">🔑 私有化大模型</span> — 支持接入企业自有的本地大模型（如 Ollama、私有化 API），所有数据处理均在内部完成。</li>
             <li><span style="color: #fbbf24;">📜 合规保障</span> — 严格遵循《个人信息保护法》《数据安全法》及审计底稿保密要求，不存储任何源文件与提取结果。</li>
             <li><span style="color: #fbbf24;">🛡️ 零数据残留</span> — 所有上传文件在处理完成后即时删除，不留痕迹。</li>
         </ul>
         <p style="color: #cbd5e1; margin-top: 1rem;">
             无论是四大会计师事务所还是企业内审部门，均可放心将 AuditFlow 嵌入现有审计流程。
         </p>
     </div>
     """, unsafe_allow_html=True)
 
 # -------------------- 页脚 --------------------
 
EOF
)
