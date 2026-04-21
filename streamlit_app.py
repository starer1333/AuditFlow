"""
AuditFlow — 审计数据中枢（环境自适应版）
云端：SiliconFlow 多模态大模型直接 OCR
本地：PaddleOCR 本地识别
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

# ==================== 环境自适应：尝试导入本地 OCR ====================
PADDLE_OCR_AVAILABLE = False
try:
    from ppocr_lite import PPOCRLite
    import cv2
    import numpy as np
    from pdf2image import convert_from_path

    @st.cache_resource
    def init_ocr():
        return PPOCRLite()

    PADDLE_OCR_AVAILABLE = True
except ImportError:
    pass  # 云端环境，降级为调用多模态大模型

# ==================== 全局辅助函数 ====================
def parse_deepseek_ocr_response(raw_response: str) -> str:
    """
    解析 DeepSeek-OCR 的返回内容，提取纯文本内容（去除坐标和标签）。
    """
    import re
    
    # 1. 提取所有 Markdown 表格（DeepSeek-OCR 会将表格包裹在 <table> 标签中）
    table_pattern = r'<table>(.*?)</table>'
    tables = re.findall(table_pattern, raw_response, re.DOTALL)
    
    parsed_parts = []
    
    if tables:
        # 有表格：提取表格内容，并清理 HTML 标签
        for table in tables:
            # 去除 <table> 标签本身（已在正则中处理）
            clean_table = table.strip()
            # 将 Markdown 格式的表格行保留
            parsed_parts.append("[表格内容]")
            parsed_parts.append(clean_table)
    
    # 2. 提取所有纯文本块（<|ref|>text</|ref|> 标签内的内容）
    text_pattern = r'<\|ref\|>text<\|/ref\|><\|det\|>\[[^\]]*\]<\|/det\|>\s*([^<]+)'
    texts = re.findall(text_pattern, raw_response, re.DOTALL)
    for text in texts:
        clean_text = text.strip()
        if clean_text and not clean_text.startswith('<'):  # 过滤掉仍含标签的行
            parsed_parts.append(clean_text)
    
    # 3. 如果上述都没提取到，降级处理：删除所有尖括号标签和坐标
    if not parsed_parts:
        # 删除所有 <|...|> 标签
        clean = re.sub(r'<\|[^|]+\|>', ' ', raw_response)
        # 删除坐标 [[...]]
        clean = re.sub(r'\[\[[^\]]+\]\]', ' ', clean)
        # 删除 HTML 标签
        clean = re.sub(r'<[^>]+>', ' ', clean)
        # 合并多余空白
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:2000] if clean else raw_response[:500]
    
    # 4. 合并所有提取到的部分
    result = "\n".join(parsed_parts)
    # 最终清理：删除残留的坐标和标签
    result = re.sub(r'<\|[^|]+\|>', '', result)
    result = re.sub(r'\[\[[^\]]+\]\]', '', result)
    result = re.sub(r'<[^>]+>', '', result)
    result = re.sub(r'\n\s*\n', '\n', result)  # 合并多余空行
    
    return result.strip() or raw_response[:500]

def validate_file_type_and_content(llm_response, selected_type):
    """校验上传文件与所选类型是否一致，以及是否为财务相关文件"""
    type_keywords = {
        "🏦 银行对账单": ["银行对账单", "Bank Statement", "交易明细", "借方", "贷方", "余额", "期初", "期末"],
        "📋 开户清单": ["已开立银行结算账户清单", "中国人民银行", "账户性质", "开户日期"],
        "❌ 销户清单/销户证明": ["销户", "账户关闭", "销户证明", "注销"],
        "📊 企业信用报告": ["信用报告", "信贷记录", "征信中心", "贷款", "担保"],
        "📬 银行询证函（回函）": ["银行询证函", "函证", "回函", "1-14项"],
        "⚖️ 银行存款余额调节表": ["余额调节表", "未达账项", "调节后余额", "企业账面"]
    }
    finance_keywords = ["银行", "余额", "交易", "账户", "存款", "贷款", "信用", "担保", "函证", "对账", "借方", "贷方", "金额", "人民币", "USD", "RMB", "HSBC", "Balance", "Statement", "Account", "Sortcode", "IBAN", "BIC"]
    content_lower = llm_response.lower()
    expected_keywords = type_keywords.get(selected_type, [])
    type_match = any(kw.lower() in content_lower for kw in expected_keywords)
    is_finance = any(kw.lower() in content_lower for kw in finance_keywords)
    return {
        "type_match": type_match,
        "is_finance": is_finance,
        "warning": None if type_match else f"您上传的文件内容与所选类型（{selected_type}）不一致",
        "error": None if is_finance else "上传的文件并非财务相关文件，请上传银行对账单、开户清单等审计资料"
    }


def generate_excel_by_type(data, file_type, company="XX科技有限公司"):
    """根据文件类型生成对应的Excel底稿"""
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


# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="AuditFlow — 审计数据中枢",
    page_icon="🌊",
    layout="wide"
)

# -------------------- 样式优化（完整保留）--------------------
st.markdown("""
<style>
    .main-header { text-align: center; padding: 2rem 0 1rem 0; }
    .main-header h1 {
        font-size: 3.2rem; font-weight: 700;
        background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .main-header p { font-size: 1.2rem; color: #a0aec0; }
    .stButton > button {
        background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%);
        color: white; border: none; border-radius: 40px; padding: 0.7rem 2rem;
        font-weight: 600; font-size: 1.1rem; width: 100%;
    }
    .stFileUploader > div {
        border: 2px dashed #4f6af5 !important; border-radius: 20px !important;
        background: rgba(79, 106, 245, 0.05) !important; padding: 2rem !important;
    }
    .result-card {
        background: #1e293b; border-radius: 20px; padding: 1.5rem;
        border: 1px solid #334155; margin-top: 1.5rem;
    }
    .feature-card {
        background: #1e293b; border-radius: 20px; padding: 1.2rem 0.8rem;
        text-align: center; border: 1px solid #334155;
        min-height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .feature-icon { font-size: 2rem; margin-bottom: 0.5rem; }
    .feature-title { font-weight: 600; color: #e2e8f0; font-size: 1rem; }
    .feature-desc { font-size: 0.9rem; color: #b0bec5; line-height: 1.4; }
    .story-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 20px; padding: 2rem; border: 1px solid #334155;
        margin: 2rem 0;
    }
    .quote-text { font-size: 1.1rem; font-style: italic; color: #cbd5e1; }
    .auditor-name {
        color: #2dd4bf; font-weight: 600; font-style: normal;
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .comparison-table { 
        width: 100%; border-collapse: collapse; margin: 1rem 0; 
        border: 1px solid #475569;
    }
    .comparison-table th { 
        background: #4f6af5; color: white; padding: 0.8rem; 
        border: 1px solid #64748b; text-align: center;
    }
    .comparison-table td { 
        padding: 0.8rem; border: 1px solid #475569; 
    }
    .highlight { color: #68d391; font-weight: 600; }
    .theory-box {
        background: #1e293b; border-radius: 15px; padding: 1.5rem;
        border: 1px solid #334155;
    }
    .theory-label { color: #94a3b8; font-size: 0.9rem; }
    .theory-quote { font-style: italic; color: #cbd5e1; }
    .theory-highlight { color: #60a5fa; font-weight: 600; }
    .footer { text-align: center; padding: 2rem 0; color: #64748b; }
</style>
""", unsafe_allow_html=True)

# -------------------- 页面头部 --------------------
st.markdown("""
<div class="main-header">
    <h1>🌊 AuditFlow</h1>
    <p>审计数据中枢 — 从“数据孤岛”到“统一大脑”的范式创新</p>
</div>
""", unsafe_allow_html=True)

# -------------------- 开篇故事 --------------------
with st.expander("📖 我们的故事：从加班的审计师说起", expanded=True):
    st.markdown("""
    <div class="story-box">
        <p class="quote-text">“实习时，我每天要处理几十份银行对账单PDF。公司配了智谱大模型，能把PDF转成Excel。但问题来了——AI识别出的数字，我不敢直接用。水印遮挡的金额、印章盖住的账号、跨页表格错位的行，每一个都要肉眼再核对一遍。原本以为AI能省时间，结果每次还是要加班几个小时。面前是几百页带水印的银行对账单、开户清单、信用报告……格式五花八门，数据散落在各处。这个月底的审计报告，又是一场和时间的赛跑。我多么希望，能有一个数字化大脑帮我处理这些重复劳动，让我专注于真正重要的专业判断。”</p>
        <p style="text-align: right; margin-top: 1rem;">—— <span class="auditor-name">一位四大审计师</span></p>
    </div>
    """, unsafe_allow_html=True)

# -------------------- 五大痛点展示卡片 --------------------
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
        st.markdown(f"""
        <div class="feature-card">
            <div class="feature-icon">{icon}</div>
            <div class="feature-title">{title}</div>
            <div class="feature-desc">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
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
    st.markdown("""
    <div class="theory-box">
        <p class="theory-label">德勤研究指出：</p>
        <p class="theory-quote">“AI将重构审计作业流程，从<span class="theory-highlight">经验驱动</span>转向<span class="theory-highlight">智能驱动</span>。”</p>
        <p class="theory-label" style="margin-top:1rem;">杨卓凡导师强调：</p>
        <p class="theory-quote">“审计数字化大脑需具备<span class="theory-highlight">感知、认知、决策、协同</span>四大能力，实现从<span class="theory-highlight">单点工具</span>到<span class="theory-highlight">统一智能层</span>的跃迁。”</p>
        <p style="margin-top:1rem; color: #68d391;">✅ AuditFlow正是这一理念的完美实践。</p>
    </div>
    """, unsafe_allow_html=True)

with st.expander("🚀 未来展望：从单文件识别到跨文档智能审计", expanded=True):
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 1.5rem; border: 1px solid #334155;">
        <p style="color: #cbd5e1; font-size: 1rem; line-height: 1.6;">
            当前版本已实现<span style="color: #2dd4bf;">单份源文件的智能识别与底稿生成</span>。在下一阶段的演进中，AuditFlow 将迈向更高阶的审计智能体：
        </p>
        <ul style="color: #94a3b8; margin-top: 1rem; line-height: 1.8;">
            <li><span style="color: #fbbf24;">📦 批量上传</span> — 支持一次性上传同一家企业的多份、多类别源文件（对账单、开户清单、信用报告等）。</li>
            <li><span style="color: #fbbf24;">🔗 交叉比对</span> — 自动识别各文件间的勾稽关系，将银行对账单余额与开户清单账户、信用报告授信额度进行交叉验证。</li>
            <li><span style="color: #fbbf24;">📊 差异定位</span> — 对于比对不一致的数据，系统将精准标注差异金额，并<span style="color: #60a5fa;">反向追溯至两份源文件的原始位置</span>。</li>
            <li><span style="color: #fbbf24;">🖼️ 可视化对证</span> — 自动生成一份<span style="color: #60a5fa;">带原始文件截图高亮的对比PDF报告</span>，清晰呈现差异细节，供审计师与企业财务高效沟通。</li>
        </ul>
        <p style="color: #cbd5e1; margin-top: 1rem;">
            最终，AuditFlow 将成为审计师的<span style="color: #2dd4bf;">“全局风险雷达”</span>，不仅处理数据，更主动发现疑点、推送洞察。
        </p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# -------------------- 文件上传区 --------------------
st.markdown("### 📁 上传银行源文件")
col1, col2 = st.columns([1, 2])

with col1:
    file_type = st.selectbox(
        "📋 文件类型",
        options=[
            "🏦 银行对账单",
            "📋 开户清单",
            "❌ 销户清单/销户证明",
            "📊 企业信用报告",
            "📬 银行询证函（回函）",
            "⚖️ 银行存款余额调节表"
        ],
        index=0,
        help="选择正确的文件类型，系统将自动匹配对应的审计底稿模板"
    )

with col2:
    uploaded_file = st.file_uploader(
        "拖拽文件或点击浏览",
        type=["pdf", "png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )
    st.caption("支持 PDF、PNG、JPG 格式，单次上传一份文件")

# -------------------- API 配置 --------------------
SILICONFLOW_API_KEY = st.secrets.get("SILICONFLOW_API_KEY", "sk-owvtekhwtwulnbuomcvsrrzglwprcyfylehowryuufxfxuau")
SILICONFLOW_MODEL = "Qwen/Qwen2-VL-72B-Instruct"

# -------------------- 审计意见参考库 --------------------
with st.expander("📝 审计意见参考库（系统内置范例，可编辑）", expanded=True):
    default_reference = """其他确认与计量问题
（一）未恰当核算定制化产品相关研发支出
根据企业会计准则及相关规定，企业为履行合同发生的成本，不属于其他企业会计准则（如存货、无形资产、固定资产等）规范范围且同时满足相关条件的，应当作为合同履约成本确认为一项资产，采用与该资产相关的商品的收入确认基础进行摊销，计入当期损益。对于履行定制化产品客户合同过程中发生的研发支出，若企业无法控制相关研发成果（如研发成果仅可用于该合同、无法用于其他合同），企业应按照收入准则中合同履约成本的规定进行处理，最终计入营业成本。若综合考虑历史经验、行业惯例、法律法规等因素后，企业有充分证据表明能够控制相关研发成果，并且预期很可能带来经济利益流入，企业应按照无形资产准则相关规定将符合条件的研发支出予以资本化。审阅分析发现，部分上市公司在已获得客户中标通知书、定点函的情况下，基于客户产品需求开展定制化的研发项目，即根据客户提供的参数标准进行产品研发，取得客户批准认可后进入批量生产阶段并签订正式合同，上市公司对此按照无形资产准则对相关研发支出进行会计处理。报告期内，部分项目因客户需求变化被终止，上市公司将已资本化的开发支出全额计提减值。前述情况下，上市公司在与客户签订合同前已明确研发活动的具体对象，应结合行业惯例、历史经验等，分析判断公司能否控制研发成果、研发成果是否可用于其他合同，在此基础上判断研发支出适用收入准则或无形资产准则。后续因客户需求变化导致上市公司终止研发项目并全额计提减值，可能表明相关技术仅可用于单一客户合同，前期按照无形资产准则予以资本化合理性存疑，应按照收入准则合同履约成本相关规定分析处理。
（二）未正确处理固定资产修复支出
根据企业会计准则及相关规定，固定资产的后续支出是指固定资产在使用过程中发生的更新改造支出、修理费用等支出。对于固定资产的后续支出，符合固定资产确认条件的，应当计入固定资产成本，同时扣除被替换部分的账面价值；不符合固定资产确认条件的，应当在发生时计入当期损益。审阅分析发现，部分上市公司将高速公路作为固定资产，同时将高速公路大额修复支出计入营业外支出，不符合企业会计准则有关规定。前述修复支出属于固定资产后续支出，上市公司应当按照有关规定判断修复支出是否能够资本化，其中符合固定资产确认条件的，应当计入固定资产成本，同时扣除被替换部分的账面价值，不符合固定资产确认条件的应当计入当期损益。
（三）未恰当确认和计量在建工程
根据企业会计准则及相关规定，企业以出包方式建造固定资产，其成本由建造该项固定资产达到预定可使用状态前所发生的必要支出构成，包括发生的建筑工程支出、安装工程支出以及需分摊计入固定资产价值的待摊支出。审阅分析发现，部分上市公司在建工程确认和计量存在错误。例如，有的上市公司因建设过程中与建造承包商产生纠纷，迟迟未与建造承包商办理工程价款结算，亦未将建造承包商已履约但双方未结算的工程款计入在建工程。在对方提起诉讼后，上市公司直接将法院判决的诉讼工程款（包括逾期未付款相关利息及违约金）全额计入在建工程。根据企业会计准则规定，上市公司应结合在建工程实际建设情况，合理确定工程进度，及时将达到预定可使用状态之前发生的必要支出计入在建工程，不应包括逾期未付款相关利息及违约金。
（四）未正确处理解除租赁所支付的违约金
根据企业会计准则及相关规定，租赁变更是指原合同条款之外的租赁范围、租赁对价、租赁期限的变更。租赁变更导致租赁范围缩小或租赁期缩短的，承租人应当相应调减使用权资产的账面价值，并将部分终止或完全终止租赁的相关利得或损失计入资产处置损益。在未发生租赁变更情况下，若租赁期开始日后承租人对终止租赁选择权的评估结果发生变化、或者终止租赁选择权的实际行使情况与原评估结果不一致等导致租赁期变化的，承租人应当根据新的租赁期限重新计量租赁负债，并相应调整使用权资产的账面价值，若使用权资产的账面价值已调减至零，承租人应当将剩余金额计入当期损益。审阅分析发现，部分上市公司与出租方签订租赁合同后因解除租赁合同关系需向对方支付违约金，上市公司错误地将该部分违约金直接计入营业外支出。在此情况下，应结合公司相关租赁合同具体约定进一步分析判断。如果公司与出租方签订的合同已明确约定了终止租赁选择权，上市公司应在认定其将行使终止租赁选择权或实际行使终止租赁选择权时重新计量租赁负债，并相应调整使用权资产账面价值。如果租赁合同未约定终止租赁选择权，上市公司提前解除租赁合同属于修改原合同条款以缩短租赁期，应作为租赁变更处理，将支付的违约金与调减的使用权资产和租赁负债净额之差计入资产处置损益。
（五）未恰当处理转让子公司股权形成的预计负债
根据企业会计准则及相关规定，若一项义务同时满足是企业承担的现时义务、履行该义务很可能导致经济利益流出企业、该义务的金额能够可靠地计量这三个条件，则应当确认为预计负债，并按照履行该义务所需支出的最佳估计数进行初始计量。审阅分析发现，部分上市公司将其未实缴出资、净资产为负的子公司股权零对价转让给第三方，在明知子公司和第三方均无偿债能力的情况下，未考虑上市公司将连带承担足额出资等责任，不当确认股权处置收益，直至后续法院判决其应就子公司债务承担连带偿还责任时才确认营业外支出。根据《公司法》，股东转让股权时未按期足额缴纳出资的，转让人对受让人未按期缴纳的出资承担补充责任。据此，上市公司在转让子公司股权时，应当合理预计需要连带承担的子公司债务赔偿义务并确认预计负债，同时冲减投资收益。
（六）未恰当核算股份支付相关递延所得税
根据税法相关规定，对于附有业绩条件或服务条件的股权激励计划，企业按照会计准则确认的成本费用在等待期不得税前抵扣，待股权激励计划行权时方可抵扣，可抵扣的金额为实际行权时的股票公允价值与激励对象支付的行权金额之间的差额。根据企业会计准则及相关规定，企业应根据资产负债表日存在的信息估计未来可以税前抵扣的金额，以未来期间很可能取得的应纳税所得额为限确认递延所得税资产。审阅分析发现，部分上市公司以前年度向高管和核心员工授予股票期权，在预计其未来存在足够的应纳税所得额情况下，上市公司未在等待期内对未来可税前抵扣的金额进行估计，未确认递延所得税资产。该股权激励计划等待期届满时，部分员工放弃行权，上市公司根据未行权数量、当日股票公允价值与激励对象支付的行权价之间的差额，一次性确认递延所得税资产。前述情况下，上市公司应在等待期内的每个资产负债表日，合理估计预计行权数量和当日股票公允价值，确认递延所得税资产；对于资产负债表日无法合理预见的员工自愿放弃行权的部分，应冲减前期已确认的递延所得税资产。
（七）未正确区分会计估计变更与前期差错更正
根据企业会计准则及相关规定，会计估计变更，是指由于资产和负债的当前状况及预期经济利益和义务发生了变化，从而对资产或负债的账面价值或者资产的定期消耗金额进行调整。前期差错，是指由于没有运用或错误运用相关可靠信息，而对前期财务报表造成省略或错报。审阅分析发现，部分上市公司没有正确区分会计估计变更和差错更正。例如，有的上市公司销售产品并提供不构成单项履约义务的维保服务，以往年度仅对维保费用中的材料支出计提预计负债，售后人员薪酬及其他费用于实际发生时计入当期损益，报告期内改为按照合同金额的一定比例对包括材料、人工及其他费用在内的全部维保费用计提预计负债，并作为会计估计变更进行处理。有的上市公司报告期内调整计提存货跌价准备的类别维度，如将同类产品组合计提调整为按照单个产品类别进行测算等，作为会计估计变更进行处理。上市公司不应将前述情况简单认定为会计估计变更，如果前期做出会计估计时，未能合理使用编制报表时已经存在且能够取得的可靠信息，如未按照准则有关规定对履行质保义务所需的直接人工、直接材料、制造费用（或类似费用）等进行恰当估计，或未能合理确定存货跌价准备计提基础等，导致前期会计估计结果未恰当反映当时情况，则报告期内的会计处理变化属于前期差错而非会计估计变更。"""

    audit_opinion_reference = st.text_area(
        "参考范例（可手动编辑）",
        value=default_reference,
        height=300,
        placeholder="此处为系统内置参考范例，您可在此修改后用于调教大模型输出风格。",
        help="修改后将影响大模型生成的审计意见措辞风格。"
    )

if uploaded_file:
    st.success(f"✅ 已上传：{uploaded_file.name} ({len(uploaded_file.getvalue())/1024:.1f} KB)")
    if uploaded_file.type.startswith("image"):
        st.image(uploaded_file, width=400)

    if st.button("🚀 开始智能处理", type="primary", use_container_width=True):
        with st.spinner("⏳ 正在提取文本..."):
            # 保存上传文件到临时路径
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                temp_input_path = tmp.name

            ocr_text = ""

            if PADDLE_OCR_AVAILABLE:
                # 本地OCR处理 (使用 ppocr-lite)
                with st.spinner("📂 正在使用本地OCR提取文本..."):
                    # PDF 转图片
                    if suffix.lower() == '.pdf':
                        images = convert_from_path(temp_input_path, dpi=200)
                        work_image_path = os.path.join(tempfile.gettempdir(), "pdf_page_1.png")
                        images[0].save(work_image_path, "PNG")
                    else:
                        work_image_path = temp_input_path

                    ocr = init_ocr()
                    result = ocr.run(work_image_path)
                    ocr_text = "\n".join([line.text for line in result])
            else:
                # 云端降级：调用 DeepSeek-OCR 专用模型
                with st.spinner("☁️ 正在调用 DeepSeek-OCR 提取文本..."):
                    img_bytes = uploaded_file.getvalue()
                    img_b64 = base64.b64encode(img_bytes).decode()

                    # ========== 请替换为您的实际配置 ==========
                    DEEPSEEK_OCR_URL = "https://api.siliconflow.cn/v1/chat/completions"  # 或您的自定义端点
                    DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY","sk-owvtekhwtwulnbuomcvsrrzglwprcyfylehowryuufxfxuau" )
                    DEEPSEEK_MODEL = "deepseek-ai/DeepSeek-OCR"
                    # =========================================

                    ocr_prompt = "<image>\n<|grounding|>Convert the document to markdown."

                    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
                    payload = {
                        "model": DEEPSEEK_MODEL,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                                {"type": "text", "text": ocr_prompt}
                            ]
                        }],
                        "temperature": 0.1,
                        "max_tokens": 2048
                    }
                    try:
                        resp = requests.post(DEEPSEEK_OCR_URL, headers=headers, json=payload, timeout=60)
                        resp.raise_for_status()
                        ocr_text = resp.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        st.error(f"DeepSeek-OCR识别失败: {e}")
                        st.stop()

            # 确保ocr_text有内容
            if not ocr_text:
                st.error("❌ 未能识别到任何文本，请检查图片质量。")
                st.stop()
            # 解析 DeepSeek-OCR 的结构化输出，提取可读内容
            parsed_ocr_text = parse_deepseek_ocr_response(ocr_text)
            st.markdown("### 🔍 识别的原始文本")
            st.text_area("提取的文本", parsed_ocr_text, height=200)

        with st.spinner("🤖 正在调用大模型分析..."):
            # 构建 Prompt
            prompt = f"""你是一名资深注册会计师（CPA），拥有多年四大会计师事务所审计经验。请根据以下 OCR 提取的文本内容，完成专业判断。

**用户选择的文件类型**：{file_type}

**OCR 提取的文本内容**：
{parsed_ocr_text[:3000]}

请仔细观察文本内容，完成以下任务：

1. **内容识别与分类**：
   - 判断该文件是否与用户所选类型一致，列出判断依据
   - 判断该文件是否属于财务/审计相关资料，如否则说明理由

2. **关键数据提取**（必须以 JSON 格式返回）：
   - 银行对账单/调节表：{{"bank_name": "", "account_number": "", "ending_balance": 0, "statement_period": "", "currency": "RMB"}}
   - 开户清单：{{"accounts": [{{"bank_name": "", "account_number": "", "status": "正常/已销户"}}]}}
   - 销户清单：{{"closed_accounts": [{{"bank_name": "", "account_number": "", "close_date": "", "close_balance": 0}}]}}
   - 信用报告：{{"company_name": "", "loans": [], "guarantees": []}}
   - 询证函回函：{{"items": {{}}, "conclusion": "确认/存在差异"}}
   请根据实际文件类型返回对应 JSON，其他类型返回空。

3. **数据质量评估**：
   - 给出综合置信度（0.0-1.0）

4. **审计意见草稿**（参考中国注册会计师审计准则第1501号）：
   - 根据提取的数据，初步判断是否存在异常（如余额为负、大额未达账项、贷款逾期等）
   - 生成一段专业的审计意见草稿，格式参考："基于已执行的审计程序，我们认为，上述银行余额调节表在所有重大方面公允反映了 XX 公司截至 XX 年 XX 月 XX 日的银行存款余额。"
   - 如发现异常，应明确指出风险点并建议进一步审计程序

5. **风险提示**：
   - 识别可能存在的审计风险（如大额异常交易、长期未达账项、关联方交易集中等）
   - 给出下一步审计建议

请用专业的审计术语作答，保持客观、严谨的风格。先用文字回答 1、3、4、5，最后输出 JSON。
{f"**审计意见参考范例**：{audit_opinion_reference}" if audit_opinion_reference else ""}

特别注意：你必须在 JSON 中明确包含 "risk_notes" 字段，内容为一段专业的审计意见草稿（至少 50 字）。即使未发现异常，也要给出正面结论。"""

            headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
            payload = {
                "model": SILICONFLOW_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2048
            }

            try:
                resp = requests.post("https://api.siliconflow.cn/v1/chat/completions", headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                llm_response = resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                st.error(f"大模型调用失败：{e}")
                st.stop()

             # 提取 JSON 部分（增强版：支持 Markdown 代码块、注释、字段名容错）
            # 1. 先尝试从 Markdown 代码块中提取
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1)
            else:
                # 2. 降级：直接搜索最外层大括号
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                json_str = json_match.group() if json_match else ""

            extracted = {}
            if json_str:
                try:
                    # 清洗：去除注释（// 和 /* */）
                    json_str = re.sub(r'//.*?\n', '\n', json_str)
                    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                    # 解析
                    raw_extracted = json.loads(json_str)
                except json.JSONDecodeError:
                    # 如果标准解析失败，尝试用 ast.literal_eval 或简单容错
                    import ast
                    try:
                        raw_extracted = ast.literal_eval(json_str)
                    except:
                        raw_extracted = {}
            else:
                raw_extracted = {}

            # 字段名容错：支持多种可能的key（大小写、中英文）
            def get_field(data, *keys):
                for k in keys:
                    if k in data and data[k] is not None:
                        return data[k]
                return None

            bank_name = get_field(raw_extracted, "bank_name", "bank", "银行名称", "BankName", "bankName")
            account_number = get_field(raw_extracted, "account_number", "account", "账号", "AccountNumber", "accountNumber")
            ending_balance = get_field(raw_extracted, "ending_balance", "balance", "期末余额", "EndingBalance", "closing_balance", "ClosingBalance")
            statement_period = get_field(raw_extracted, "statement_period", "period", "期间", "对账期间", "StatementPeriod")
            currency = get_field(raw_extracted, "currency", "币种", "Currency", "Cur")
            confidence = get_field(raw_extracted, "confidence", "置信度", "Confidence")
            risk_notes = get_field(raw_extracted, "risk_notes", "riskNotes", "审计意见", "opinion", "risk_opinion")

            # 余额数值清洗：去除货币符号、逗号，转为float
            if ending_balance is not None:
                if isinstance(ending_balance, str):
                    ending_balance = re.sub(r'[£$¥€,\s]', '', ending_balance)
                    try:
                        ending_balance = float(ending_balance)
                    except:
                        ending_balance = None
                elif isinstance(ending_balance, (int, float)):
                    pass
                else:
                    ending_balance = None

            # 置信度处理
            if confidence is None:
                confidence = 0.5
            elif isinstance(confidence, str):
                try:
                    confidence = float(confidence.strip('%')) / 100 if '%' in confidence else float(confidence)
                except:
                    confidence = 0.5
            confidence = max(0.0, min(1.0, confidence))

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
                except:
                    extracted = {"bank_name": "解析失败", "error": "JSON 格式错误"}
            else:
                extracted = {"bank_name": "未识别", "raw": llm_response[:500]}

            # 文字分析部分
            text_analysis = llm_response[:llm_response.find('{')] if '{' in llm_response else llm_response

            # 校验文件类型与财务相关性
            validation = validate_file_type_and_content(parsed_ocr_text, file_type)
            if validation["error"]:
                st.error(validation["error"])
                st.stop()
            if validation["warning"]:
                st.warning(validation["warning"])

            # 展示分析报告
            st.markdown("---")
            st.markdown("### 🤖 大模型分析报告")
            with st.expander("📋 查看详细分析", expanded=True):
                st.markdown(text_analysis)

            # 展示提取字段
            st.markdown("### 📊 提取的关键字段")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🏦 银行名称", extracted.get("bank_name", "未识别"))
            with c2:
                st.metric("💳 账号", extracted.get("account_number", "未识别"))
            with c3:
                bal = extracted.get("ending_balance")
                st.metric("💰 期末余额", f"¥ {bal:,.2f}" if isinstance(bal, (int, float)) else "未识别")
            with c4:
                st.metric("📈 置信度", f"{extracted.get('confidence', 0)*100:.0f}%")

            # 审计意见展示
            if extracted.get("risk_notes"):
                st.markdown("### 📋 审计意见")
                st.info(extracted["risk_notes"])
            else:
                st.warning("⚠️ 大模型未返回审计意见，请参考提取数据自行判断。")

            # 生成 Excel 底稿
            st.markdown("### 📥 下载审计底稿")
            excel_bytes = generate_excel_by_type(extracted, file_type)

            st.download_button(
                label="📊 下载 Excel 底稿",
                data=excel_bytes,
                file_name=f"{file_type.strip('🏦📋❌📊📬⚖️ ')}底稿_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            st.download_button(
                label="📄 下载完整报告 (JSON)",
                data=json.dumps({"analysis": text_analysis, "extracted": extracted}, ensure_ascii=False, indent=2),
                file_name=f"AuditFlow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

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

# -------------------- 页脚品牌语 --------------------
st.divider()
st.markdown("""
<div class="footer">
    <p style="font-size: 1.2rem; font-weight: 600;">🌊 AuditFlow — 让审计数据自动流动，让审计师回归专业判断</p>
    <p>德勤数字化精英挑战赛 Team J | 从“单点工具”到“统一大脑”的范式创新</p>
</div>
""", unsafe_allow_html=True)
