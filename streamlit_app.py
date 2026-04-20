"""
AuditFlow — UI 界面
纯前端展示，调用已有处理模块
"""

import streamlit as st
import os
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# 导入您的功能模块（根据实际文件名）
import format_and_clean
import ocr_extract
import validate_and_map
import generate_report
# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="AuditFlow — 审计数据中枢",
    page_icon="🌊",
    layout="wide"
)

# -------------------- 样式（保持您原来的样式）--------------------
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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🌊 AuditFlow</h1>
    <p>审计数据中枢 — 从任意格式到标准化底稿</p>
</div>
""", unsafe_allow_html=True)

# -------------------- 文件类型选择 --------------------
st.markdown("### 📁 选择文件类型并上传")
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
        index=0
    )

with col2:
    uploaded_file = st.file_uploader(
        "拖拽文件或点击浏览",
        type=["pdf", "png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )

# -------------------- 处理按钮 --------------------
if uploaded_file:
    st.success(f"✅ 已上传：{uploaded_file.name} ({len(uploaded_file.getvalue())/1024:.1f} KB)")
    
    if st.button("🚀 开始智能处理", type="primary", use_container_width=True):
        with st.spinner("⏳ 正在处理中，请稍候..."):
            # 保存临时文件
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            # ========== 调用您的处理函数 ==========
            # 这里假设您的函数返回一个字典，包含提取的数据和 Excel 文件路径
            # 请根据实际情况调整参数和返回值
            result = process_audit_file(
                file_path=tmp_path,
                file_type=file_type,
                original_filename=uploaded_file.name
            )
            
            # 假设 result 包含：
            #   - result['extracted_data']: dict，提取的字段
            #   - result['excel_path']: str，生成的 Excel 文件路径
            #   - result['report']: str，风险分析报告（可选）
            
            extracted = result.get('extracted_data', {})
            excel_path = result.get('excel_path', '')
            report = result.get('report', '')
            
            # ---------- 展示结果 ----------
            st.markdown("---")
            st.markdown("### 📊 提取结果")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🏦 银行名称", extracted.get('bank_name', '未识别'))
            with c2:
                st.metric("💳 账号", extracted.get('account_number', '未识别'))
            with c3:
                bal = extracted.get('ending_balance')
                st.metric("💰 期末余额", f"¥ {bal:,.2f}" if bal else "未识别")
            with c4:
                st.metric("📈 置信度", f"{extracted.get('confidence', 0)*100:.0f}%")
            
            if report:
                st.info(f"📋 {report}")
            
            # ---------- 下载 Excel ----------
            if excel_path and os.path.exists(excel_path):
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="📊 下载 Excel 底稿",
                        data=f,
                        file_name=os.path.basename(excel_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.warning("未生成 Excel 文件")

# -------------------- 页脚 --------------------
st.divider()
st.caption("🌊 AuditFlow | 德勤数字化精英挑战赛 Team J")
