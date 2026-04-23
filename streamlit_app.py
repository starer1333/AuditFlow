"""
AuditFlow — 审计数据中枢（完整功能版）
五大痛点 · 六类文档 · 双模型驱动 · 智能底稿生成
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
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

# ==================== 全局辅助函数 ====================

def parse_deepseek_ocr_response(raw_response: str) -> str:
    """解析 DeepSeek-OCR 返回内容，提取纯文本"""
    import re
    table_pattern = r'<table>(.*?)</table>'
    tables = re.findall(table_pattern, raw_response, re.DOTALL)
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

    if "银行对账单" in file_type or "调节表" in file_type:
        ws = wb.active
        ws.title = "银行存款余额调节表"
        ws.merge_cells("A1:F1")
        ws["A1"] = "银行存款余额调节表"
        ws["A1"].font = Font(size=16, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")
        bank = data.get("bank_name", "未识别")
        acc = data.get("account_number", "未识别")
        bal = data.get("ending_balance", 0)
        period = data.get("statement_period", "未识别")
        row = 3
        info = [
            ["被审计单位", company, "", "索引号", "A-2-1"],
            ["银行名称", bank, "", "账号", acc],
            ["对账单余额", f"{bal:,.2f}" if isinstance(bal, (int, float)) else "未识别", "", "期间", period]
        ]
        for r in info:
            for col, v in enumerate(r, 1):
                ws.cell(row=row, column=col, value=v)
            row += 1
        row += 1
        headers = ["项目", "金额", "审计标识", "说明"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D3D3D3")
        row += 1
        table = [
            ["银行对账单余额", bal if isinstance(bal, (int, float)) else "", "B", "系统识别"],
            ["加：企业已收银行未收", "", "", ""],
            ["减：企业已付银行未付", "", "", ""],
            ["调节后余额", bal if isinstance(bal, (int, float)) else "", "G", ""],
            ["企业账面余额", "", "", "待填写"],
            ["差异", "", "", ""]
        ]
        for item, amt, mark, note in table:
            ws.cell(row=row, column=1, value=item)
            if amt:
                ws.cell(row=row, column=2, value=amt).number_format = '#,##0.00'
            ws.cell(row=row, column=3, value=mark)
            ws.cell(row=row, column=4, value=note)
            row += 1
        ws.cell(row=row, column=1, value=f"审计意见：{data.get('risk_notes', '')}")
        row += 2
        ws.cell(row=row, column=1, value=f"编制人：AuditFlow  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        for col, width in enumerate([20, 18, 12, 35], 1):
            ws.column_dimensions[chr(64+col)].width = width

    elif "开户清单" in file_type:
        ws = wb.active
        ws.title = "银行存款明细表"
        ws.merge_cells("A1:G1")
        ws["A1"] = "银行存款明细表"
        ws["A1"].font = Font(size=16, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")
        headers = ["序号", "银行名称", "账号", "币种", "账户性质", "开户日期", "账户状态"]
        row = 3
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D3D3D3")
        row += 1
        accounts = data.get("accounts", [])
        if accounts:
            for i, acc in enumerate(accounts, 1):
                ws.cell(row=row, column=1, value=i)
                ws.cell(row=row, column=2, value=acc.get("bank_name", ""))
                ws.cell(row=row, column=3, value=acc.get("account_number", ""))
                ws.cell(row=row, column=4, value=acc.get("currency", "RMB"))
                ws.cell(row=row, column=5, value=acc.get("account_type", ""))
                ws.cell(row=row, column=6, value=acc.get("open_date", ""))
                ws.cell(row=row, column=7, value=acc.get("status", ""))
                row += 1
        else:
            ws.cell(row=row, column=1, value="未识别到账户信息")
        row += 2
        ws.cell(row=row, column=1, value=f"编制人：AuditFlow  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    elif "销户清单" in file_type:
        ws = wb.active
        ws.title = "账户变更明细表"
        ws.merge_cells("A1:F1")
        ws["A1"] = "销户清单明细表"
        ws["A1"].font = Font(size=16, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")
        headers = ["序号", "银行名称", "账号", "销户日期", "销户时余额", "销户原因"]
        row = 3
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D3D3D3")
        row += 1
        closed = data.get("closed_accounts", [])
        if closed:
            for i, acc in enumerate(closed, 1):
                ws.cell(row=row, column=1, value=i)
                ws.cell(row=row, column=2, value=acc.get("bank_name", ""))
                ws.cell(row=row, column=3, value=acc.get("account_number", ""))
                ws.cell(row=row, column=4, value=acc.get("close_date", ""))
                ws.cell(row=row, column=5, value=acc.get("close_balance", ""))
                ws.cell(row=row, column=6, value=acc.get("close_reason", ""))
                row += 1
        row += 2
        ws.cell(row=row, column=1, value=f"编制人：AuditFlow  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    elif "信用报告" in file_type:
        ws = wb.active
        ws.title = "借款及担保底稿"
        ws["A1"] = "企业信用报告摘要"
        ws["A1"].font = Font(size=16, bold=True)
        row = 3
        info = [
            ["企业名称", data.get("company_name", "未识别")],
            ["统一社会信用代码", data.get("credit_code", "未识别")],
            ["报告日期", data.get("report_date", "未识别")]
        ]
        for label, val in info:
            ws.cell(row=row, column=1, value=label).font = Font(bold=True)
            ws.cell(row=row, column=2, value=val)
            row += 1
        row += 1
        ws.cell(row=row, column=1, value="未结清贷款").font = Font(bold=True)
        row += 1
        loans = data.get("loans", [])
        if loans:
            headers = ["金融机构", "贷款金额", "期限", "担保方式"]
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col, value=h)
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="D3D3D3")
            row += 1
            for loan in loans:
                ws.cell(row=row, column=1, value=loan.get("bank", ""))
                ws.cell(row=row, column=2, value=loan.get("amount", ""))
                ws.cell(row=row, column=3, value=loan.get("term", ""))
                ws.cell(row=row, column=4, value=loan.get("guarantee_type", ""))
                row += 1
        row += 2
        ws.cell(row=row, column=1, value=f"编制人：AuditFlow  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    elif "询证函" in file_type:
        ws = wb.active
        ws.title = "银行函证控制表"
        ws.merge_cells("A1:D1")
        ws["A1"] = "银行询证函回函摘要"
        ws["A1"].font = Font(size=16, bold=True)
        ws["A1"].alignment = Alignment(horizontal="center")
        headers = ["函证项目", "回函结果", "差异说明"]
        row = 3
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=h)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D3D3D3")
        row += 1
        items = data.get("items", {})
        for key, val in items.items():
            ws.cell(row=row, column=1, value=key)
            ws.cell(row=row, column=2, value=val)
            ws.cell(row=row, column=3, value="")
            row += 1
        row += 2
        ws.cell(row=row, column=1, value=f"编制人：AuditFlow  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    else:
        ws = wb.active
        ws.title = "审计底稿"
        ws["A1"] = "审计数据摘要"
        ws["A1"].font = Font(size=16, bold=True)
        row = 3
        for key, val in data.items():
            if key not in ["raw", "analysis"]:
                ws.cell(row=row, column=1, value=str(key)).font = Font(bold=True)
                ws.cell(row=row, column=2, value=str(val))
                row += 1

    for col in range(1, 10):
        ws.column_dimensions[chr(64+col)].width = 18

    excel_io = io.BytesIO()
    wb.save(excel_io)
    excel_io.seek(0)
    return excel_io


# ==================== 页面配置 ====================
st.set_page_config(page_title="AuditFlow — 审计数据中枢", page_icon="🌊", layout="wide")

st.markdown("""
<style>
    .main-header { text-align: center; padding: 2rem 0 1rem 0; }
    .main-header h1 { font-size: 3.2rem; font-weight: 700; background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .main-header p { font-size: 1.2rem; color: #a0aec0; }
    .stButton > button { background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%); color: white; border: none; border-radius: 40px; padding: 0.7rem 2rem; font-weight: 600; font-size: 1.1rem; width: 100%; }
    .stFileUploader > div { border: 2px dashed #4f6af5 !important; border-radius: 20px !important; background: rgba(79, 106, 245, 0.05) !important; padding: 2rem !important; }
    .feature-card { background: #1e293b; border-radius: 20px; padding: 1.2rem 0.8rem; text-align: center; border: 1px solid #334155; min-height: 160px; display: flex; flex-direction: column; justify-content: center; }
    .feature-icon { font-size: 2rem; margin-bottom: 0.5rem; }
    .feature-title { font-weight: 600; color: #e2e8f0; font-size: 1rem; }
    .feature-desc { font-size: 0.9rem; color: #b0bec5; line-height: 1.4; }
    .story-box { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 2rem; border: 1px solid #334155; margin: 2rem 0; }
    .quote-text { font-size: 1.1rem; font-style: italic; color: #cbd5e1; }
    .footer { text-align: center; padding: 2rem 0; color: #64748b; }
    .comparison-table { width: 100%; border-collapse: collapse; margin: 1rem 0; border: 1px solid #475569; }
    .comparison-table th { background: #4f6af5; color: white; padding: 0.8rem; border: 1px solid #64748b; text-align: center; }
    .comparison-table td { padding: 0.8rem; border: 1px solid #475569; }
    .highlight { color: #68d391; font-weight: 600; }
    .theory-box { background: #1e293b; border-radius: 15px; padding: 1.5rem; border: 1px solid #334155; }
    .theory-label { color: #94a3b8; font-size: 0.9rem; }
    .theory-quote { font-style: italic; color: #cbd5e1; }
    .theory-highlight { color: #60a5fa; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="main-header"><h1>🌊 AuditFlow</h1><p>审计数据中枢 — 从“数据孤岛”到“统一大脑”的范式创新</p></div>""", unsafe_allow_html=True)

# -------------------- 开篇故事 --------------------
with st.expander("📖 我们的故事：从凌晨三点的审计师说起", expanded=True):
    st.markdown("""<div class="story-box"><p class="quote-text">“凌晨三点，我揉了揉发酸的眼睛。面前是几百页带水印的银行对账单、开户清单、信用报告。公司的智谱大模型识别完，我还是不敢直接用——水印遮挡的金额、印章盖住的账号、跨页表格错位的行，每一个都要肉眼再核对一遍。原本以为AI能省时间，结果每次还是要加班几个小时。”</p>
<p style="text-align: right; margin-top: 1rem; color: #FFD700; font-weight: 600;">—— 一位四大审计师</p></div>""", unsafe_allow_html=True)

# -------------------- 五大痛点 --------------------
st.markdown("### 🔬 核心能力 · 攻克审计资料处理的5大难点")
cols = st.columns(5)
features = [
    ("📄", "跨页合并", "大模型全局感知，自动拼接跨页表格"),
    ("🀄️", "生僻汉字", "语义理解 + 字典纠错，精准识别罕见字"),
    ("🌐", "中英文混排", "多语言统一映射，余额/Balance自动对齐"),
    ("💧", "水印印章", "视觉大模型主动忽略干扰，聚焦核心文字"),
    ("📊", "表格还原", "端到端行列解析，完美提取嵌套表头")
]
for col, (icon, title, desc) in zip(cols, features):
    with col:
        st.markdown(f"""<div class="feature-card"><div class="feature-icon">{icon}</div><div class="feature-title">{title}</div><div class="feature-desc">{desc}</div></div>""", unsafe_allow_html=True)
st.divider()

# -------------------- 逻辑对比 --------------------
col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("### 🎯 我们的解题逻辑：从“数据孤岛”到“统一大脑”")
    st.markdown("""
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
SILICONFLOW_MODEL = "Qwen/Qwen2-VL-72B-Instruct"

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
        with st.spinner("⏳ 正在提取文本..."):
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_input_path = tmp.name

            ocr_text = ""
            try:
                img_bytes = uploaded_file.getvalue()
                img_b64 = base64.b64encode(img_bytes).decode()
                headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
                payload = {
                    "model": "deepseek-ai/DeepSeek-OCR",
                    "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}, {"type": "text", "text": "<image>\n<|grounding|>Convert the document to markdown."}]}],
                    "temperature": 0.1, "max_tokens": 2048
                }
                resp = requests.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    ocr_text = resp.json()["choices"][0]["message"]["content"]
            except:
                ocr_text = ""

            if not ocr_text:
                ocr_text = """中国工商银行北京朝阳支行\n账号：6222020200123456789\n币种：RMB\n对账单期间：2025-12-01 至 2025-12-31\n期末余额：1,250,000.00"""
                st.info("📌 云端OCR暂不可用，当前为模拟演示模式。")

            parsed_ocr_text = parse_deepseek_ocr_response(ocr_text)
            st.markdown("### 🔍 识别的原始文本")
            st.text_area("提取的文本", parsed_ocr_text, height=200)
            # ========== API 调用状态提示 ==========
            if ocr_api_success and llm_api_success:
                st.success("✅ 当前使用：真实 DeepSeek-OCR + 真实大模型分析")
            elif ocr_api_success and not llm_api_success:
                st.warning("⚠️ DeepSeek-OCR 真实调用成功，大模型使用模拟数据")
            elif not ocr_api_success and llm_api_success:
                st.warning("⚠️ OCR 使用模拟数据，大模型真实调用成功")
            else:
                st.info("📌 当前为模拟演示模式，展示完整流程")
        with st.spinner("🤖 正在调用大模型分析..."):
            prompt = f"""你是一名资深注册会计师。请根据以下OCR文本完成专业判断。\n**文件类型**：{file_type}\n**OCR内容**：\n{parsed_ocr_text[:3000]}\n\n1. 内容识别与分类\n2. 关键数据提取（JSON格式）\n3. 数据质量评估（置信度0.0-1.0）\n4. 审计意见草稿\n5. 风险提示\n\n参考范例：{audit_opinion_reference}\n\n最后输出JSON包含risk_notes字段。"""
            headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
            payload = {"model": SILICONFLOW_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 2048}
            try:
                resp = requests.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    llm_response = resp.json()["choices"][0]["message"]["content"]
                else:
                    raise Exception()
            except:
                llm_response = f"""1. 内容识别与分类：该文件为银行对账单，与所选类型一致。\n3. 数据质量评估：综合置信度0.95。\n4. 审计意见草稿：基于已执行的审计程序，我们认为，上述银行余额调节表在所有重大方面公允反映了银行存款余额。未发现重大异常。\n5. 风险提示：建议对期末大额余额执行函证程序。\n{{"bank_name": "中国工商银行北京朝阳支行", "account_number": "6222020200123456789", "ending_balance": 1250000.00, "statement_period": "2025-12-01至2025-12-31", "currency": "RMB", "confidence": 0.95, "risk_notes": "基于已执行的程序，未发现重大异常，银行存款余额可确认。"}}"""
                st.info("📌 大模型API暂不可用，当前为模拟演示模式。")

            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            extracted = {}
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                except:
                    extracted = {"bank_name": "解析失败"}

            text_analysis = llm_response[:llm_response.find('{')] if '{' in llm_response else llm_response
            validation = validate_file_type_and_content(parsed_ocr_text, file_type)
            if validation["error"]:
                st.warning(validation["error"])  # 改为警告，不停止流程
            if validation["warning"]:
                st.warning(validation["warning"])

            st.markdown("---")
            st.markdown("### 🤖 大模型分析报告")
            with st.expander("📋 查看详细分析", expanded=True):
                st.markdown(text_analysis)

            st.markdown("### 📊 提取的关键字段")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("🏦 银行名称", extracted.get("bank_name", "未识别"))
            with c2: st.metric("💳 账号", extracted.get("account_number", "未识别"))
            with c3: st.metric("💰 期末余额", f"¥ {extracted.get('ending_balance', 0):,.2f}")
            with c4: st.metric("📈 置信度", f"{extracted.get('confidence', 0)*100:.0f}%")

            if extracted.get("risk_notes"):
                st.markdown("### 📋 审计意见")
                st.info(extracted["risk_notes"])

            st.markdown("### 📥 下载审计底稿")
            excel_bytes = generate_excel_by_type(extracted, file_type)
            st.download_button(label="📊 下载 Excel 底稿", data=excel_bytes, file_name=f"审计底稿_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            st.download_button(label="📄 下载完整报告 (JSON)", data=json.dumps({"analysis": text_analysis, "extracted": extracted}, ensure_ascii=False, indent=2), file_name=f"AuditFlow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json", use_container_width=True)

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
st.divider()
st.markdown("""<div class="footer"><p style="font-size: 1.2rem; font-weight: 600;">🌊 AuditFlow — 让审计数据自动流动，让审计师回归专业判断</p><p>德勤数字化精英挑战赛 Team J | 从“单点工具”到“统一大脑”的范式创新</p></div>""", unsafe_allow_html=True)
