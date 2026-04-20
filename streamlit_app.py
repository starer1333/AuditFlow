"""
AuditFlow — 审计数据中枢
OCR + 多模态大模型协同审计
德勤数字化精英挑战赛 Team J
"""

import streamlit as st
import json
import re
import base64
from datetime import datetime
import requests

# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="AuditFlow — 审计数据中枢",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------- 样式优化 --------------------
st.markdown("""
<style>
    .main-header { text-align: center; padding: 1.5rem 0 1rem 0; }
    .main-header h1 {
        font-size: 3.2rem; font-weight: 700; margin-bottom: 0.3rem;
        background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .main-header p { font-size: 1.2rem; color: #a0aec0; }
    .feature-card {
        background: #1e293b; border-radius: 20px; padding: 1.5rem 0.8rem;
        text-align: center; border: 1px solid #334155;
        display: flex; flex-direction: column; align-items: center;
        justify-content: flex-start; min-height: 220px;
    }
    .feature-icon { font-size: 2.2rem; margin-bottom: 0.8rem; }
    .feature-title { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.5rem; }
    .feature-desc { font-size: 0.8rem; color: #94a3b8; line-height: 1.4; }
    .result-card { background: #1e293b; border-radius: 20px; padding: 1.5rem; border: 1px solid #334155; margin-top: 1.5rem; }
    .stButton > button {
        background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%);
        color: white; border: none; border-radius: 40px; padding: 0.7rem 2rem;
        font-weight: 600; font-size: 1.1rem; transition: all 0.2s; border: 1px solid #4f6af5;
    }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 0 20px rgba(79, 106, 245, 0.4); }
    .stFileUploader > div {
        border: 2px dashed #4f6af5 !important; border-radius: 20px !important;
        background: rgba(79, 106, 245, 0.05) !important; padding: 2rem !important;
    }
    .diff-table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    .diff-table th, .diff-table td { padding: 0.5rem; border: 1px solid #334155; text-align: left; }
    .diff-table th { background: #2d3748; }
    .ocr-value { color: #f6ad55; }
    .llm-value { color: #63b3ed; }
    .fusion-value { color: #68d391; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# -------------------- 页面头部 --------------------
st.markdown("""
<div class="main-header">
    <h1>🌊 AuditFlow</h1>
    <p>OCR + 多模态大模型协同审计 · 双重校验确保数据可靠</p>
</div>
""", unsafe_allow_html=True)


# -------------------- 五大核心能力 --------------------
st.markdown("### 🔬 协同处理 · 五大难题一站式解决")
cols = st.columns(5)

features = [
    ("📄", "跨页合并", "OCR提取表格结构，大模型语义拼接"),
    ("🀄️", "生僻汉字", "OCR字符识别+大模型语义推断"),
    ("🌐", "中英文混排", "OCR多语言识别+大模型字段映射"),
    ("💧", "水印印章", "大模型视觉抗干扰，OCR专注文字"),
    ("📊", "表格还原", "OCR行列检测+大模型结构理解")
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


# -------------------- 文件上传区 --------------------
st.markdown("### 📁 上传银行源文件")
uploaded_file = st.file_uploader(
    "拖拽文件到这里，或点击浏览",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=False,
    label_visibility="collapsed"
)

if uploaded_file is not None:
    file_size = len(uploaded_file.getvalue()) / 1024
    st.success(f"✅ 已上传：{uploaded_file.name} ({file_size:.1f} KB)")
    if uploaded_file.type.startswith("image"):
        st.image(uploaded_file, caption="上传的图片", use_container_width=True, width=400)


# -------------------- 处理按钮 --------------------
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    process_clicked = st.button(
        "🚀 开始协同处理",
        use_container_width=True,
        type="primary",
        disabled=uploaded_file is None
    )


# ==================== 模拟OCR提取函数 ====================
def simulate_ocr_extraction():
    """
    模拟OCR引擎的提取结果。
    在实际本地部署中，这里会调用PaddleOCR。
    OCR的特点：字符识别准确，但易受水印/印章干扰，缺乏语义理解。
    """
    return {
        "bank_name": "中国工商很行北京朝阳支行",  # OCR可能把"银行"误识别为"很行"
        "account_number": "6222020200123456789",
        "ending_balance": "1,250,000.00",  # 带千分位逗号
        "statement_period": "2025-12-01至2025-12-31",
        "raw_text": "中国工商很行北京朝阳支行\n账号：6222020200123456789\n期末余额：1,250,000.00\n对账期间：2025-12-01至2025-12-31",
        "confidence": 0.82,
        "issues": ["疑似水印干扰导致'银行'误识别为'很行'"]
    }


# ==================== 大模型视觉分析函数 ====================
def encode_image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')


def call_multimodal_llm(image_bytes, ocr_result):
    """
    调用多模态大模型进行视觉分析和语义校验。
    大模型的特点：抗干扰能力强，能理解语义，但可能忽略细节字符。
    """
    img_base64 = encode_image_to_base64(image_bytes)
    
    prompt = f"""你是一个专业的审计资料处理专家。请仔细观察这张银行对账单图片。

已知OCR引擎提取了以下内容（可能存在错误）：
- 银行名称：{ocr_result['bank_name']}
- 账号：{ocr_result['account_number']}
- 期末余额：{ocr_result['ending_balance']}
- 期间：{ocr_result['statement_period']}

请你完成以下任务：
1. **视觉校验**：检查OCR结果是否正确。特别关注：
   - 是否有水印、印章遮挡导致OCR误识别？
   - 是否有生僻汉字被OCR错误识别？
   - 是否有中英文混排被OCR忽略？
2. **字段修正**：根据你从图片中直接看到的内容，修正OCR可能错误的字段。
3. **补充信息**：提取OCR可能遗漏的信息（如币种、银行英文缩写等）。
4. **风险提示**：根据交易流水，简要指出需要关注的异常点。

请按以下格式返回JSON：
{{
  "corrected_bank_name": "修正后的银行名称",
  "corrected_account_number": "修正后的账号",
  "corrected_balance": 修正后的期末余额（纯数字）,
  "currency": "币种",
  "statement_period": "期间",
  "corrections_made": ["修正项1", "修正项2"],
  "llm_confidence": 0.95,
  "risk_notes": "风险提示"
}}
"""
    
    # 模拟大模型返回（实际部署时替换为真实API调用）
    # 大模型能识别出"很行"应该是"银行"
    return {
        "corrected_bank_name": "中国工商银行北京朝阳支行",
        "corrected_account_number": "6222020200123456789",
        "corrected_balance": 1250000.00,
        "currency": "RMB",
        "statement_period": "2025-12-01至2025-12-31",
        "corrections_made": ["将OCR误识别的'很行'修正为'银行'", "去除余额中的千分位逗号"],
        "llm_confidence": 0.95,
        "risk_notes": "账户余额较大，建议函证确认；未发现异常大额波动。"
    }


# ==================== 融合决策函数 ====================
def fuse_results(ocr_result, llm_result):
    """
    融合OCR和大模型的结果，采用高置信度优先策略：
    - 如果大模型明确修正了某字段，采纳大模型结果
    - 如果大模型置信度高于OCR，采纳大模型结果
    - 否则保留OCR结果
    """
    fused = {}
    
    # 银行名称：大模型修正优先
    fused["bank_name"] = llm_result["corrected_bank_name"]
    
    # 账号：两者一致则采纳，否则以大模型为准
    if ocr_result["account_number"] == llm_result["corrected_account_number"]:
        fused["account_number"] = ocr_result["account_number"]
        fused["account_source"] = "OCR+LLM一致"
    else:
        fused["account_number"] = llm_result["corrected_account_number"]
        fused["account_source"] = "LLM修正"
    
    # 余额：统一转为数字
    fused["ending_balance"] = llm_result["corrected_balance"]
    fused["currency"] = llm_result.get("currency", "RMB")
    fused["statement_period"] = llm_result["statement_period"]
    
    # 融合置信度
    fused["confidence"] = max(ocr_result.get("confidence", 0), llm_result.get("llm_confidence", 0))
    
    # 修正记录
    fused["corrections"] = llm_result.get("corrections_made", [])
    fused["risk_notes"] = llm_result.get("risk_notes", "")
    
    return fused


# ==================== 主处理流程 ====================
if process_clicked and uploaded_file is not None:
    
    # ---------- 步骤1：OCR提取 ----------
    with st.spinner("🔍 步骤1：OCR引擎正在提取文字..."):
        ocr_result = simulate_ocr_extraction()
    
    st.markdown("---")
    st.markdown("### 📝 步骤1：OCR提取结果")
    st.caption("OCR特点：字符识别准确，但易受水印/印章干扰，缺乏语义理解")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏦 银行名称", ocr_result["bank_name"])
    with col2:
        st.metric("💳 账号", ocr_result["account_number"])
    with col3:
        st.metric("💰 期末余额", ocr_result["ending_balance"])
    
    if ocr_result.get("issues"):
        st.warning(f"⚠️ OCR识别到的问题：{', '.join(ocr_result['issues'])}")
    
    # ---------- 步骤2：大模型视觉分析 ----------
    with st.spinner("🤖 步骤2：多模态大模型正在视觉分析..."):
        llm_result = call_multimodal_llm(uploaded_file.getvalue(), ocr_result)
    
    st.markdown("---")
    st.markdown("### 🤖 步骤2：大模型视觉分析结果")
    st.caption("大模型特点：抗干扰能力强，能理解语义，自动修正OCR错误")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏦 修正后银行名称", llm_result["corrected_bank_name"])
    with col2:
        st.metric("💳 修正后账号", llm_result["corrected_account_number"])
    with col3:
        st.metric("💰 修正后余额", f"{llm_result['corrected_balance']:,.2f}")
    
    if llm_result.get("corrections_made"):
        st.info(f"🔧 大模型做出的修正：{', '.join(llm_result['corrections_made'])}")
    
    # ---------- 步骤3：融合结果 ----------
    fused_result = fuse_results(ocr_result, llm_result)
    
    st.markdown("---")
    st.markdown("### ✨ 步骤3：OCR + 大模型融合结果")
    st.caption("融合策略：大模型修正优先，两者一致则直接采纳")
    
    # 对比表格
    st.markdown("""
    <table class="diff-table">
        <tr><th>字段</th><th>OCR原始结果</th><th>大模型修正</th><th>最终采纳</th></tr>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <tr>
        <td>银行名称</td>
        <td class="ocr-value">{ocr_result['bank_name']}</td>
        <td class="llm-value">{llm_result['corrected_bank_name']}</td>
        <td class="fusion-value">{fused_result['bank_name']}</td>
    </tr>
    <tr>
        <td>账号</td>
        <td class="ocr-value">{ocr_result['account_number']}</td>
        <td class="llm-value">{llm_result['corrected_account_number']}</td>
        <td class="fusion-value">{fused_result['account_number']}<br><small>({fused_result['account_source']})</small></td>
    </tr>
    <tr>
        <td>期末余额</td>
        <td class="ocr-value">{ocr_result['ending_balance']}</td>
        <td class="llm-value">{llm_result['corrected_balance']:,.2f}</td>
        <td class="fusion-value">{fused_result['ending_balance']:,.2f}</td>
    </tr>
    </table>
    """, unsafe_allow_html=True)
    
    # 最终结果卡片
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown("#### 🎯 最终审计数据")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🏦 银行名称", fused_result["bank_name"])
    with c2:
        st.metric("💳 账号", fused_result["account_number"])
    with c3:
        st.metric("💰 期末余额", f"{fused_result['currency']} {fused_result['ending_balance']:,.2f}")
    with c4:
        st.metric("📈 综合置信度", f"{fused_result['confidence']*100:.0f}%")
    
    if fused_result.get("risk_notes"):
        st.info(f"📋 风险提示：{fused_result['risk_notes']}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ---------- 下载 ----------
    st.markdown("### 📥 下载融合结果")
    
    full_report = {
        "ocr_result": ocr_result,
        "llm_result": llm_result,
        "fused_result": fused_result,
        "timestamp": datetime.now().isoformat()
    }
    
    st.download_button(
        label="📄 下载完整审计报告（JSON）",
        data=json.dumps(full_report, ensure_ascii=False, indent=2),
        file_name=f"AuditFlow_Fusion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True
    )


# -------------------- 页脚 --------------------
st.divider()
st.caption("🌊 AuditFlow — OCR + 大模型协同审计 | 德勤数字化精英挑战赛 Team J")
st.caption("💡 云端兼容版：展示OCR与大模型的差异对比与融合决策。本地部署可接入真实PaddleOCR。")
