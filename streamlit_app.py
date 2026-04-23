"""
AuditFlow — 审计数据中枢（最终演示版）
零API依赖降级策略 · 100%跑通流程
德勤数字化精英挑战赛 Team J
"""

import streamlit as st
import io
import re
import base64
import json
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

# ==================== 全局辅助函数 ====================

def validate_file_type_and_content(text_content, selected_type):
    """校验上传文件与所选类型是否一致，以及是否为财务相关文件"""
    type_keywords = {
        "🏦 银行对账单": ["银行对账单", "Bank Statement", "交易明细", "借方", "贷方", "余额", "期初", "期末"],
        "📋 开户清单": ["已开立银行结算账户清单", "中国人民银行", "账户性质", "开户日期"],
        "❌ 销户清单/销户证明": ["销户", "账户关闭", "销户证明", "注销"],
        "📊 企业信用报告": ["信用报告", "信贷记录", "征信中心", "贷款", "担保"],
        "📬 银行询证函（回函）": ["银行询证函", "函证", "回函", "1-14项"],
        "⚖️ 银行存款余额调节表": ["余额调节表", "未达账项", "调节后余额", "企业账面"]
    }
    finance_keywords = ["银行", "余额", "交易", "账户", "存款", "贷款", "信用", "担保", "函证", "对账", "金额", "HSBC", "Balance", "Statement", "Account"]
    content_lower = text_content.lower()
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
st.set_page_config(page_title="AuditFlow — 审计数据中枢", page_icon="🌊", layout="wide")

# -------------------- 样式优化 --------------------
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
</style>
""", unsafe_allow_html=True)

# -------------------- 页面头部 --------------------
st.markdown("""<div class="main-header"><h1>🌊 AuditFlow</h1><p>审计数据中枢 — 从“数据孤岛”到“统一大脑”的范式创新</p></div>""", unsafe_allow_html=True)

# -------------------- 开篇故事 --------------------
with st.expander("📖 我们的故事：从加班的审计师说起", expanded=True):
    st.markdown("""<div class="story-box"><p class="quote-text">“实习时，我每天要处理几十份银行对账单PDF。公司配了智谱大模型，能把PDF转成Excel。但问题来了——AI识别出的数字，我不敢直接用。水印遮挡的金额、印章盖住的账号、跨页表格错位的行，每一个都要肉眼再核对一遍。原本以为AI能省时间，结果每次还是要加班几个小时。”</p><p style="text-align: right; margin-top: 1rem;">—— 一位审计实习生</p></div>""", unsafe_allow_html=True)

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
        st.markdown(f"""<div class="feature-card"><div class="feature-icon">{icon}</div><div class="feature-title">{title}</div><div class="feature-desc">{desc}</div></div>""", unsafe_allow_html=True)
st.divider()

# -------------------- 文件上传区 --------------------
st.markdown("### 📁 上传银行源文件")
col1, col2 = st.columns([1, 2])
with col1:
    file_type = st.selectbox("📋 文件类型", options=["🏦 银行对账单", "📋 开户清单", "❌ 销户清单/销户证明", "📊 企业信用报告", "📬 银行询证函（回函）", "⚖️ 银行存款余额调节表"], index=0)
with col2:
    uploaded_file = st.file_uploader("拖拽文件或点击浏览", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed")
    st.caption("支持 PDF、PNG、JPG 格式")

# -------------------- 审计意见参考库 --------------------
with st.expander("📝 审计意见参考库（系统内置范例，可编辑）", expanded=True):
    default_reference = """基于已执行的审计程序，我们认为，上述银行余额调节表在所有重大方面公允反映了XX公司截至XX年XX月XX日的银行存款余额。对于大额未达账项，已建议企业检查期后银行对账单并进行调整。未发现其他异常交易或重大错报风险。"""
    audit_opinion_reference = st.text_area("参考范例（可手动编辑）", value=default_reference, height=150)

# -------------------- 核心处理逻辑（演示版） --------------------
if uploaded_file:
    st.success(f"✅ 已上传：{uploaded_file.name}")
    if uploaded_file.type.startswith("image"):
        st.image(uploaded_file, width=400)

    if st.button("🚀 开始智能处理", type="primary", use_container_width=True):
        with st.spinner("⏳ 正在提取文本..."):
            # ========== 模拟OCR识别结果 ==========
            ocr_text = """中国工商银行北京朝阳支行
账号：6222020200123456789
币种：RMB
对账单期间：2025-12-01 至 2025-12-31
期初余额：1,000,000.00
期末余额：1,250,000.00
交易明细：
2025-12-05 支付货款 -50,000.00
2025-12-10 收到货款 +200,000.00"""
            st.info("📌 当前为模拟演示模式，展示完整流程。")
            st.markdown("### 🔍 识别的原始文本")
            st.text_area("提取的文本", ocr_text, height=200)

        with st.spinner("🤖 正在调用大模型分析..."):
            # ========== 模拟大模型分析报告 ==========
            llm_response = """1. 内容识别与分类：该文件为银行对账单，与用户所选类型一致，属于财务相关资料。

3. 数据质量评估：综合置信度0.95。

4. 审计意见草稿：基于已执行的审计程序，我们认为，上述银行余额调节表在所有重大方面公允反映了XX公司截至2025年12月31日的银行存款余额。未发现重大异常。

5. 风险提示：未发现大额异常交易或关联方交易集中，建议关注期末大额余额的函证程序。

{
  "bank_name": "中国工商银行北京朝阳支行",
  "account_number": "6222020200123456789",
  "ending_balance": 1250000.00,
  "statement_period": "2025-12-01至2025-12-31",
  "currency": "RMB",
  "confidence": 0.95,
  "risk_notes": "基于已执行的程序，未发现重大异常，银行存款余额可确认。建议对期末大额余额执行函证程序。"
}"""
            st.info("📌 大模型API暂不可用，当前为模拟演示模式，展示完整流程。")

            # 提取 JSON 部分
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            extracted = {}
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                except:
                    extracted = {"bank_name": "解析失败", "error": "JSON格式错误"}
            
            text_analysis = llm_response[:llm_response.find('{')] if '{' in llm_response else llm_response

            validation = validate_file_type_and_content(ocr_text, file_type)
            if validation["error"]:
                st.error(validation["error"])
                st.stop()
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

# -------------------- 数据安全与隐私保护 --------------------
with st.expander("🔒 数据安全与隐私保护", expanded=True):
    st.markdown("""<div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 20px; padding: 1.5rem; border: 1px solid #334155;"><p style="color: #cbd5e1;">AuditFlow 将数据安全置于首位，支持私有化部署与内网隔离，遵循《个人信息保护法》及审计底稿保密要求，所有上传文件处理完成后即时删除。</p></div>""", unsafe_allow_html=True)

# -------------------- 页脚 --------------------
st.divider()
st.markdown("""<div class="footer"><p style="font-size: 1.2rem; font-weight: 600;">🌊 AuditFlow — 让审计数据自动流动，让审计师回归专业判断</p><p>德勤数字化精英挑战赛 Team J | 从“单点工具”到“统一大脑”的范式创新</p></div>""", unsafe_allow_html=True)
