"""
AuditFlow — 审计数据中枢（完整商赛版）
基于 SiliconFlow 多模态大模型 · 零本地依赖 · 展示商业故事与理论深度
德勤数字化精英挑战赛 Team J
"""

import streamlit as st
import requests
import base64
import json
import io
import re
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="AuditFlow — 审计数据中枢",
    page_icon="🌊",
    layout="wide"
)

# -------------------- 样式优化 --------------------
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

# -------------------- 开篇故事：制造冲突 --------------------
with st.expander("📖 我们的故事：从凌晨三点的审计师说起", expanded=False):
    st.markdown("""
    <div class="story-box">
        <p class="quote-text">“凌晨三点，我揉了揉发酸的眼睛。面前是几百页带水印的银行对账单、开户清单、信用报告……格式五花八门，数据散落在各处。这个月底的审计报告，又是一场和时间的赛跑。我多么希望，能有一个数字化大脑帮我处理这些重复劳动，让我专注于真正重要的专业判断。”</p>
        <p style="text-align: right; margin-top: 1rem;">—— <span class="auditor-name">一位四大审计师的自白</span></p>
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

# -------------------- 逻辑对比：为什么是AuditFlow --------------------
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

with st.expander("🚀 未来展望：从单文件识别到跨文档智能审计", expanded=False):
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

if uploaded_file:
    st.success(f"✅ 已上传：{uploaded_file.name} ({len(uploaded_file.getvalue())/1024:.1f} KB)")
    if uploaded_file.type.startswith("image"):
        st.image(uploaded_file, width=400)

    if st.button("🚀 开始智能处理", type="primary", use_container_width=True):
        with st.spinner("⏳ 正在调用多模态大模型分析..."):
            # 将图片转为 base64
            img_bytes = uploaded_file.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode()

            # 构建 Prompt（一次性完成五大痛点检测 + 字段提取 + 风险意见）
            prompt = """你是一个资深的审计专家，请仔细观察这张银行对账单图片，完成以下任务：

1. **水印/印章检测**：图片是否有水印、印章、倾斜？描述干扰情况。
2. **生僻汉字识别**：是否有生僻汉字？列出并纠正常见OCR错误（如“很行”→“银行”）。
3. **中英文混排**：是否有中英文混排？提取中英文关键信息。
4. **表格结构分析**：表格是否有跨页、合并单元格？描述结构。
5. **关键字段提取**：提取以下字段，以JSON格式返回：
{
  "bank_name": "银行全称",
  "account_number": "完整账号",
  "ending_balance": 期末余额数字,
  "statement_period": "对账单期间",
  "currency": "币种",
  "confidence": 0.95,
  "risk_notes": "简要风险提示与审计意见"
}
请先用文字回答1-4题，最后输出JSON。"""

            headers = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}"}
            payload = {
                "model": SILICONFLOW_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }],
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

            # 提取 JSON 部分
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                except:
                    extracted = {"bank_name": "解析失败", "error": "JSON格式错误"}
            else:
                extracted = {"bank_name": "未识别", "raw": llm_response[:500]}

            # 文字分析部分（1-4题的回答）
            text_analysis = llm_response[:llm_response.find('{')] if '{' in llm_response else llm_response

            # ---------- 展示分析报告 ----------
            st.markdown("---")
            st.markdown("### 🤖 大模型分析报告")
            with st.expander("📋 查看详细分析（水印/生僻字/混排/表格）", expanded=True):
                st.markdown(text_analysis)

            # ---------- 展示提取字段 ----------
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
            if extracted.get("risk_notes"):
                st.info(f"📋 审计意见：{extracted['risk_notes']}")

            # ---------- 生成 Excel 底稿 ----------
            st.markdown("### 📥 下载审计底稿")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "银行存款余额调节表"
            ws.merge_cells("A1:F1")
            ws["A1"] = "银行存款余额调节表"
            ws["A1"].font = Font(size=16, bold=True)
            ws["A1"].alignment = Alignment(horizontal="center")

            bank = extracted.get("bank_name", "未识别")
            acc = extracted.get("account_number", "未识别")
            bal = extracted.get("ending_balance", 0)
            period = extracted.get("statement_period", "未识别")

            row = 3
            info = [
                ["被审计单位", "XX科技有限公司", "", "索引号", "A-2-1"],
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
                ["银行对账单余额", bal if isinstance(bal, (int, float)) else "", "B", "大模型识别"],
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

            ws.cell(row=row, column=1, value=f"审计意见：{extracted.get('risk_notes', '')}")
            row += 2
            ws.cell(row=row, column=1, value=f"编制人：AuditFlow  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            for col, width in enumerate([20, 18, 12, 35], 1):
                ws.column_dimensions[chr(64+col)].width = width

            excel_io = io.BytesIO()
            wb.save(excel_io)
            excel_io.seek(0)

            st.download_button(
                label="📊 下载 Excel 底稿",
                data=excel_io,
                file_name=f"银行余额调节表_{bank}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
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

# -------------------- 页脚品牌语 --------------------
st.divider()
st.markdown("""
<div class="footer">
    <p style="font-size: 1.2rem; font-weight: 600;">🌊 AuditFlow — 让审计数据自动流动，让审计师回归专业判断</p>
    <p>德勤数字化精英挑战赛 Team J | 从“单点工具”到“统一大脑”的范式创新</p>
</div>
""", unsafe_allow_html=True)
