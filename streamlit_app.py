import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
st.set_page_config(
    page_title="AuditFlow — 审计数据中枢",
    page_icon="🌊",  # 可以用 emoji 或自定义 favicon
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.markdown("### 📁 上传银行源文件")
st.markdown("*支持银行对账单、开户清单、询证函回函的扫描PDF或图片*")

uploaded_file = st.file_uploader(
    "",  # label留空，用上方的markdown说明
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=False,
    key="file_uploader"
)

if uploaded_file:
    # 显示上传成功信息
    st.success(f"✅ 已上传：{uploaded_file.name} ({uploaded_file.size/1024:.1f} KB)")
    st.markdown("### 📋 处理流程")

if st.button("🚀 开始智能处理", type="primary", use_container_width=True):
    progress_bar = st.progress(0, text="准备中...")
    
    # 步骤1：保存文件
    progress_bar.progress(10, text="保存上传文件...")
    temp_path = save_uploaded_file(uploaded_file)
    
    # 步骤2：格式检测与图像净化
    progress_bar.progress(30, text="检测文件格式并净化图像...")
    cleaned_img = step2_format_and_clean(temp_path)
    
    # 步骤3：OCR识别
    progress_bar.progress(50, text="OCR识别中（PaddleOCR）...")
    extracted_data = step3_ocr_extract(cleaned_img)
    
    # 步骤4：数据校验
    progress_bar.progress(70, text="校验账号并评估置信度...")
    validated_data = step4_validate(extracted_data)
    
    # 步骤5：生成Excel底稿
    progress_bar.progress(90, text="生成审计底稿...")
    excel_path = step5_generate_excel(validated_data)
    
    progress_bar.progress(100, text="✅ 处理完成！")
    st.markdown("### 📊 提取结果")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("银行名称", extracted_data.get("bank_name", "未识别"))
with col2:
    st.metric("账号", extracted_data.get("account_number", "未识别"))
with col3:
    balance = extracted_data.get("ending_balance", 0)
    st.metric("期末余额", f"¥ {balance:,.2f}" if balance else "未识别")
with col4:
    st.metric("置信度", f"{extracted_data.get('confidence', 0)*100:.0f}%")

# 校验结果
validation = extracted_data.get("validation", {})
if validation.get("luhn_passed"):
    st.success("✅ Luhn校验通过")
else:
    st.warning("⚠️ Luhn校验失败，账号可能不合法")

if validation.get("need_human_review"):
    st.warning("⚠️ 置信度较低，建议人工复核")
    st.markdown("### 📥 下载")

col1, col2 = st.columns(2)
with col1:
    with open(excel_path, "rb") as f:
        st.download_button(
            label="📊 下载Excel底稿",
            data=f,
            file_name=os.path.basename(excel_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
with col2:
    json_str = json.dumps(extracted_data, ensure_ascii=False, indent=2)
    st.download_button(
        label="📄 下载JSON数据",
        data=json_str,
        file_name="extracted_data.json",
        mime="application/json",
        use_container_width=True
    )
    """
AuditMind Web 交互界面
基于 Streamlit 构建，整合已有的 step2~step5 模块
"""

import os
import sys
import json
import tempfile
import streamlit as st
from datetime import datetime

# 将当前目录加入Python路径，确保能导入模块
sys.path.insert(0, os.path.dirname(__file__))

# 页面配置（必须在最前面）
st.set_page_config(
    page_title="AuditMind — 审计数据中枢",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 导入我们已有的模块函数
from step2_format_and_clean import clean_image as step2_clean
from step3_ocr_extract import extract_fields as step3_extract
from step3_ocr_extract import CLEANED_IMG
from step4_validate_and_map import luhn_check, DATA_FILE as STEP4_DATA_FILE
from step5_generate_report import generate_excel as step5_generate

# 导入OCR引擎（重用step3中的初始化逻辑）
from paddleocr import PaddleOCR
import cv2
import numpy as np
import magic
import pdfplumber
from pdf2image import convert_from_path


# ==================== 页面样式 ====================
st.markdown("""
<style>
    /* 主标题 */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .main-header h1 {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        font-size: 1.2rem;
        color: #888;
    }
    
    /* 上传区样式 */
    .upload-container {
        border: 2px dashed #667eea;
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        background: rgba(102, 126, 234, 0.05);
        margin: 2rem 0;
    }
    
    /* 结果卡片 */
    .result-card {
        background: #1e1e2f;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #333;
    }
    
    /* 步骤卡片 */
    .step-container {
        display: flex;
        justify-content: space-around;
        margin: 2rem 0;
    }
    .step-item {
        text-align: center;
        flex: 1;
    }
    .step-number {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #667eea;
        color: white;
        display: inline-block;
        line-height: 40px;
        font-weight: bold;
    }
    .step-label {
        margin-top: 0.5rem;
        font-size: 0.9rem;
        color: #aaa;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 页面头部 ====================
st.markdown("""
<div class="main-header">
    <h1>📊 AuditMind</h1>
    <p>审计数据中枢 — 从任意格式的银行源文件到标准化审计底稿，一站式自动处理</p>
</div>
""", unsafe_allow_html=True)


# ==================== 辅助函数 ====================
def save_uploaded_file(uploaded_file) -> str:
    """保存上传的文件到临时目录"""
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def process_pdf_to_image(pdf_path: str) -> str:
    """将PDF转换为图片（取第一页）"""
    images = convert_from_path(pdf_path, dpi=200)
    img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    images[0].save(img_path, "PNG")
    return img_path


def run_ocr_on_image(image_path: str) -> tuple:
    """对图片运行PaddleOCR并提取字段"""
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    result = ocr.ocr(image_path, cls=True)
    
    if not result or not result[0]:
        return "", {}
    
    text_lines = [line[1][0] for line in result[0] if line]
    full_text = "\n".join(text_lines)
    data = step3_extract(full_text)
    
    return full_text, data


# ==================== 主界面 ====================
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # 文件上传区
    st.markdown("### 📁 上传银行源文件")
    st.markdown("*支持银行对账单、开户清单、询证函回函的扫描PDF或图片*")
    
    uploaded_file = st.file_uploader(
        "",  # label留空
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=False,
        key="file_uploader"
    )
    
    # 账面余额输入
    book_balance = st.number_input(
        "📊 企业账面余额（元，可选）",
        min_value=0.0,
        step=1000.0,
        format="%.2f",
        help="如不填写，将默认与银行对账单余额一致"
    )
    
    # 处理按钮
    process_clicked = st.button(
        "🚀 开始智能处理",
        type="primary",
        use_container_width=True,
        disabled=uploaded_file is None
    )


# ==================== 处理逻辑 ====================
if uploaded_file and process_clicked:
    st.divider()
    
    # 进度条
    progress_bar = st.progress(0, text="⏳ 准备中...")
    status_text = st.empty()
    
    # 步骤1：保存文件
    progress_bar.progress(10, text="📂 保存上传文件...")
    temp_path = save_uploaded_file(uploaded_file)
    
    # 步骤2：格式检测与图像净化
    progress_bar.progress(25, text="🔍 检测文件格式...")
    
    ext = os.path.splitext(temp_path)[1].lower()
    if ext == '.pdf':
        # 判断是否为扫描件
        with pdfplumber.open(temp_path) as pdf:
            text = "".join(p.extract_text() or "" for p in pdf.pages[:3])
        if len(text.strip()) < 200:
            progress_bar.progress(35, text="📷 PDF转图片...")
            work_image = process_pdf_to_image(temp_path)
        else:
            st.error("❌ 暂不支持电子PDF，请上传扫描件")
            st.stop()
    else:
        work_image = temp_path
    
    # 图像净化
    progress_bar.progress(45, text="🎨 图像净化（去噪/水印抑制/倾斜矫正）...")
    cleaned_path = step2_clean(work_image)
    
    # 步骤3：OCR识别
    progress_bar.progress(65, text="🔎 OCR识别中（PaddleOCR）...")
    full_text, extracted_data = run_ocr_on_image(cleaned_path)
    
    # 步骤4：数据校验
    progress_bar.progress(80, text="✅ 校验数据...")
    
    acc = extracted_data.get('account_number')
    luhn_ok = luhn_check(acc) if acc else False
    
    checks = []
    if acc and luhn_ok:
        checks.append("Luhn通过")
    else:
        checks.append("Luhn失败")
    
    if extracted_data.get('ending_balance') is None:
        checks.append("无余额")
    if not extracted_data.get('bank_name'):
        checks.append("无银行名")
    
    final_confidence = extracted_data.get('confidence', 0)
    if not luhn_ok:
        final_confidence = min(final_confidence, 0.5)
    
    extracted_data['validation'] = {
        'checks': checks,
        'luhn_passed': luhn_ok,
        'final_confidence': final_confidence,
        'need_human_review': final_confidence < 0.7
    }
    
    # 步骤5：生成Excel底稿
    progress_bar.progress(90, text="📊 生成审计底稿...")
    excel_path = step5_generate(extracted_data, book_balance if book_balance > 0 else None)
    
    progress_bar.progress(100, text="🎉 处理完成！")
    status_text.success("✅ 所有步骤已完成")
    
    # ==================== 结果展示 ====================
    st.divider()
    st.markdown("### 📊 提取结果")
    
    # 指标卡片
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🏦 银行名称", extracted_data.get("bank_name") or "未识别")
    with c2:
        st.metric("💳 账号", extracted_data.get("account_number") or "未识别")
    with c3:
        bal = extracted_data.get("ending_balance")
        st.metric("💰 期末余额", f"¥ {bal:,.2f}" if bal else "未识别")
    with c4:
        st.metric("📈 置信度", f"{final_confidence*100:.0f}%")
    
    # 校验状态
    st.markdown("#### 🔍 校验结果")
    status_cols = st.columns(3)
    with status_cols[0]:
        if luhn_ok:
            st.success("✅ Luhn校验通过")
        else:
            st.error("❌ Luhn校验失败")
    with status_cols[1]:
        if final_confidence >= 0.7:
            st.success(f"✅ 置信度 {final_confidence*100:.0f}%")
        else:
            st.warning(f"⚠️ 置信度 {final_confidence*100:.0f}%，建议人工复核")
    with status_cols[2]:
        if extracted_data.get('statement_period'):
            st.info(f"📅 {extracted_data.get('statement_period')}")
        else:
            st.info("📅 期间未识别")
    
    # 原始文本预览
    with st.expander("📝 查看OCR原始文本（前500字符）"):
        st.text(full_text[:500] if full_text else "无识别结果")
    
    # 下载按钮
    st.divider()
    st.markdown("### 📥 下载")
    
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        with open(excel_path, "rb") as f:
            st.download_button(
                label="📊 下载Excel底稿",
                data=f,
                file_name=os.path.basename(excel_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    with dl_col2:
        json_str = json.dumps(extracted_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 下载JSON数据",
            data=json_str,
            file_name=f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

elif not uploaded_file:
    # 未上传文件时显示引导
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #666;">
        <p style="font-size: 3rem; margin-bottom: 1rem;">📁</p>
        <p style="font-size: 1.2rem;">请先上传银行对账单、开户清单或询证函回函</p>
        <p style="font-size: 0.9rem; color: #888;">支持 PDF、PNG、JPG 格式，最大 200MB</p>
    </div>
    """, unsafe_allow_html=True)


# ==================== 页脚 ====================
st.divider()
st.caption("AuditMind — 让审计师回归专业判断 | 德勤数字化精英挑战赛 Team J")
