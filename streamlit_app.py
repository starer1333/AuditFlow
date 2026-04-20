"""
AuditFlow — 审计数据中枢
从任意格式的银行源文件到标准化审计底稿，一站式自动处理
德勤数字化精英挑战赛 Team J
"""

import streamlit as st
import pandas as pd
import json
import base64
from datetime import datetime
from PIL import Image
import io
import os

# -------------------- 页面配置（必须放在最前面）--------------------
st.set_page_config(
    page_title="AuditFlow — 审计数据中枢",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------- 样式优化 --------------------
st.markdown("""
<style>
    /* 主色调：深海蓝紫渐变 */
    .main-header {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        margin-bottom: 1rem;
    }
    .main-header h1 {
        font-size: 3.2rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
        background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        font-size: 1.2rem;
        color: #a0aec0;
    }
    
    /* 上传区域卡片 */
    .upload-card {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 24px;
        padding: 2rem;
        border: 1px solid #334155;
        backdrop-filter: blur(10px);
        margin-bottom: 1.5rem;
    }
    
    /* 功能特性卡片 */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 1rem;
        margin: 2rem 0;
    }
    .feature-card {
        background: #1e293b;
        border-radius: 20px;
        padding: 1.5rem 1rem;
        text-align: center;
        border: 1px solid #334155;
        transition: all 0.2s;
    }
    .feature-card:hover {
        border-color: #4f6af5;
        transform: translateY(-3px);
    }
    .feature-icon {
        font-size: 2.2rem;
        margin-bottom: 0.8rem;
    }
    .feature-title {
        font-size: 1rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 0.5rem;
    }
    .feature-desc {
        font-size: 0.8rem;
        color: #94a3b8;
        line-height: 1.4;
    }
    
    /* 结果卡片 */
    .result-card {
        background: #1e293b;
        border-radius: 20px;
        padding: 1.5rem;
        border: 1px solid #334155;
        margin-top: 1.5rem;
    }
    
    /* 提示框 */
    .info-box {
        background: #1e3a5f;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #4f6af5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 40px;
        padding: 0.7rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.2s;
        border: 1px solid #4f6af5;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(79, 106, 245, 0.4);
    }
    
    /* 文件上传器 */
    .stFileUploader > div {
        border: 2px dashed #4f6af5 !important;
        border-radius: 20px !important;
        background: rgba(79, 106, 245, 0.05) !important;
        padding: 2rem !important;
    }
    
    /* 选择框 */
    .stSelectbox > div > div {
        border-radius: 40px !important;
        background: #0f172a !important;
        border: 1px solid #334155 !important;
    }
</style>
""", unsafe_allow_html=True)


# -------------------- 页面头部 --------------------
st.markdown("""
<div class="main-header">
    <h1>🌊 AuditFlow</h1>
    <p>审计数据中枢 — 从任意格式的银行源文件到标准化审计底稿，一站式智能处理</p>
</div>
""", unsafe_allow_html=True)


# -------------------- 五大核心功能卡片（对应您的5大痛点）--------------------
st.markdown("### 🔬 核心能力 · 攻克审计资料处理的5大难点")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📄➡️📑</div>
        <div class="feature-title">跨页合并与表格重建</div>
        <div class="feature-desc">智能识别跨页表格，自动拼接表头与数据行，完美还原合并单元格与嵌套结构</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🀄️</div>
        <div class="feature-title">生僻汉字精准识别</div>
        <div class="feature-desc">自建审计专用字典，覆盖GBK字符集，支持"灏、鑫、燊、懿"等银行名/企业名中的罕见字</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🌐</div>
        <div class="feature-title">中英文混排理解</div>
        <div class="feature-desc">支持中英文、数字、货币符号混合场景，自动识别并统一映射"余额/Balance"等字段</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">💧</div>
        <div class="feature-title">抗干扰水印分离</div>
        <div class="feature-desc">多模态分层文档理解，智能分离印章、水印、手写批注，保护原始数据不丢失</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📊</div>
        <div class="feature-title">复杂表格结构还原</div>
        <div class="feature-desc">自动解析无框表格、嵌套表头，精准还原行列关系，确保字段与数值对应无误</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# -------------------- 文件类型选择 + 上传区 --------------------
st.markdown("### 📁 选择文件类型并上传")
st.markdown("*请先选择您要上传的审计资料类型，然后上传对应的扫描件或图片*")

# 两列布局：左为文件类型选择，右为上传区
col_left, col_right = st.columns([1, 2])

with col_left:
    file_type = st.selectbox(
        "📋 请选择文件类型",
        options=[
            "请选择...",
            "🏦 银行对账单",
            "📋 开户清单",
            "❌ 销户清单/销户证明",
            "📊 企业信用报告",
            "📬 银行询证函（回函）",
            "⚖️ 银行存款余额调节表"
        ],
        index=0,
        help="选择正确的文件类型有助于我们使用对应的识别模板，提高准确率"
    )
    
    # 显示每种文件类型的说明
    if file_type != "请选择...":
        type_info = {
            "🏦 银行对账单": "**用途**：获取期末余额及交易流水，是调节表的核心数据源。\n\n**常见格式**：盖章PDF扫描件、图片",
            "📋 开户清单": "**用途**：验证银行账户的完整性，防止账外账户。\n\n**常见格式**：人民银行打印的盖章PDF",
            "❌ 销户清单/销户证明": "**用途**：核实当期销户的真实性，防止利用销户账户隐藏交易。\n\n**常见格式**：PDF/图片",
            "📊 企业信用报告": "**用途**：核实企业贷款、担保、抵押等信息的完整性与准确性。\n\n**常见格式**：多页PDF",
            "📬 银行询证函（回函）": "**用途**：第三方独立确认银行存款、借款、担保等14项信息。\n\n**常见格式**：盖章PDF/扫描件",
            "⚖️ 银行存款余额调节表": "**用途**：调节银行对账单余额与企业账面余额的差异。\n\n**常见格式**：Excel/PDF"
        }
        st.info(type_info.get(file_type, ""))

with col_right:
    uploaded_file = st.file_uploader(
        "拖拽文件到这里，或点击浏览",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=False,
        key="file_uploader",
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        file_size = len(uploaded_file.getvalue()) / 1024
        st.success(f"✅ 已上传：{uploaded_file.name} ({file_size:.1f} KB)")


# -------------------- 处理按钮 --------------------
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    process_clicked = st.button(
        "🚀 开始智能处理",
        use_container_width=True,
        type="primary"
    )


# -------------------- 上传/选择提示逻辑 --------------------
if process_clicked:
    # 检查是否选择了文件类型
    if file_type == "请选择...":
        st.warning("⚠️ 请先选择要上传的文件类型（如：银行对账单、开户清单等）")
    # 检查是否上传了文件
    elif uploaded_file is None:
        st.warning("⚠️ 请先上传需要处理的文件")
    else:
        # 正常处理流程
        with st.spinner("⏳ 正在处理中，请稍候..."):
            import time
            time.sleep(2)  # 模拟处理时间
            
            # 模拟提取的数据
            mock_data = {
                "bank_name": "中国工商银行北京朝阳支行",
                "account_number": "6222020200123456789",
                "ending_balance": 1250000.00,
                "statement_period": "2025-12-01 至 2025-12-31",
                "confidence": 0.87,
                "validation": {
                    "luhn_passed": True,
                    "final_confidence": 0.87,
                    "need_human_review": False
                }
            }
            
            # 根据文件类型调整模拟数据
            if "开户清单" in file_type:
                mock_data["document_type"] = "开户清单"
                mock_data["accounts"] = [
                    {"bank": "工商银行", "account": "6222****1234", "status": "正常"},
                    {"bank": "建设银行", "account": "6227****5678", "status": "正常"},
                ]
            elif "信用报告" in file_type:
                mock_data["document_type"] = "企业信用报告"
                mock_data["loans"] = [{"bank": "中国银行", "amount": 5000000, "status": "正常"}]
            elif "询证函" in file_type:
                mock_data["document_type"] = "银行询证函"
                mock_data["函证项目"] = {"存款": 1250000.00, "借款": 0, "担保": "无"}
            elif "调节表" in file_type:
                mock_data["document_type"] = "余额调节表"
                mock_data["book_balance"] = 1270000.00
                mock_data["difference"] = -20000.00
            elif "销户" in file_type:
                mock_data["document_type"] = "销户证明"
                mock_data["close_date"] = "2025-12-15"
                mock_data["close_balance"] = 0.00
            
            st.session_state['processed_data'] = mock_data
            st.session_state['processing_done'] = True
        
        st.success("✅ 处理完成！")
        st.balloons()


# -------------------- 结果展示 --------------------
if 'processing_done' in st.session_state and st.session_state['processing_done']:
    data = st.session_state['processed_data']
    
    st.divider()
    st.markdown("### 📊 提取结果")
    
    with st.container():
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        
        # 第一行：核心指标
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🏦 银行名称", data.get("bank_name", "未识别")[:15] + "..." if data.get("bank_name") and len(data.get("bank_name", "")) > 15 else data.get("bank_name", "未识别"))
        with c2:
            st.metric("💳 账号", data.get("account_number", "未识别"))
        with c3:
            bal = data.get("ending_balance")
            st.metric("💰 期末余额", f"¥ {bal:,.2f}" if bal else "未识别")
        with c4:
            conf = data.get("confidence", 0)
            st.metric("📈 置信度", f"{conf*100:.0f}%")
        
        # 第二行：校验状态
        st.markdown("#### 🔍 校验结果")
        status_cols = st.columns(3)
        with status_cols[0]:
            if data.get("validation", {}).get("luhn_passed"):
                st.success("✅ Luhn校验通过")
            else:
                st.error("❌ Luhn校验失败")
        with status_cols[1]:
            final_conf = data.get("validation", {}).get("final_confidence", 0)
            if final_conf >= 0.7:
                st.success(f"✅ 置信度 {final_conf*100:.0f}%")
            else:
                st.warning(f"⚠️ 置信度 {final_conf*100:.0f}%，建议人工复核")
        with status_cols[2]:
            st.info(f"📅 {data.get('statement_period', '未识别期间')}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 额外信息（根据文件类型展示）
    if data.get("document_type"):
        with st.expander("📄 查看详细提取内容", expanded=False):
            st.json(data)
    
    # 下载按钮
    st.divider()
    st.markdown("### 📥 下载")
    
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    with dl_col1:
        # 生成模拟Excel
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📊 下载Excel底稿（模拟）",
            data=json_str,
            file_name=f"AuditFlow_{data.get('bank_name', 'result')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            help="云端演示版输出JSON格式，本地部署可生成真实Excel"
        )
    with dl_col2:
        st.download_button(
            label="📄 下载JSON数据",
            data=json_str,
            file_name=f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    with dl_col3:
        if uploaded_file:
            st.download_button(
                label="📎 重新下载源文件",
                data=uploaded_file.getvalue(),
                file_name=uploaded_file.name,
                mime=uploaded_file.type,
                use_container_width=True
            )


# -------------------- 未处理时的引导页 --------------------
elif 'processing_done' not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 使用示例卡片
    st.markdown("### 💡 快速体验")
    st.markdown("*点击下方按钮，使用内置示例银行对账单立即体验完整流程*")
    
    col_demo1, col_demo2, col_demo3 = st.columns([1, 1, 1])
    with col_demo2:
        if st.button("🎯 使用示例文件演示", use_container_width=True):
            with st.spinner("正在处理示例文件..."):
                import time
                time.sleep(1.5)
                
                demo_data = {
                    "bank_name": "中国建设银行上海浦东支行",
                    "account_number": "6227001234567890",
                    "ending_balance": 3580000.50,
                    "statement_period": "2025-11-01 至 2025-11-30",
                    "confidence": 0.92,
                    "validation": {
                        "luhn_passed": True,
                        "final_confidence": 0.92,
                        "need_human_review": False
                    },
                    "extracted_transactions": 47,
                    "risk_notes": "未发现异常大额交易，余额与账面一致。"
                }
                st.session_state['processed_data'] = demo_data
                st.session_state['processing_done'] = True
                st.rerun()


# -------------------- 页脚 --------------------
st.divider()
st.caption("🌊 AuditFlow — 让审计数据自动流动 | 德勤数字化精英挑战赛 Team J")
st.caption("⚠️ 云端演示版使用模拟数据，展示完整交互流程。本地部署可接入真实OCR引擎。")
