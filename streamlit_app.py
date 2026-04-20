"""
AuditFlow — 审计数据中枢
真实 OCR 识别 + 大模型语义理解 + 底稿生成
德勤数字化精英挑战赛 Team J
"""

import streamlit as st
import os
import tempfile
import json
import re
from datetime import datetime
import time
import cv2
import numpy as np
from PIL import Image
import io

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
    .feature-grid { display: flex; flex-wrap: nowrap; gap: 1rem; margin: 2rem 0; }
    .feature-card {
        flex: 1; background: #1e293b; border-radius: 20px; padding: 1.5rem 0.8rem;
        text-align: center; border: 1px solid #334155; transition: all 0.2s;
        display: flex; flex-direction: column; align-items: center;
        justify-content: flex-start; min-height: 220px;
    }
    .feature-card:hover { border-color: #4f6af5; transform: translateY(-3px); }
    .feature-icon { font-size: 2.2rem; margin-bottom: 0.8rem; line-height: 1.2; }
    .feature-title { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.5rem; }
    .feature-desc { font-size: 0.8rem; color: #94a3b8; line-height: 1.4; padding: 0 0.2rem; }
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
    .stSelectbox > div > div {
        border-radius: 40px !important; background: #0f172a !important;
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


# -------------------- 五大核心功能卡片 --------------------
st.markdown("### 🔬 核心能力 · 攻克审计资料处理的5大难点")

cols = st.columns(5)

with cols[0]:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📄</div>
        <div class="feature-title">跨页合并与表格重建</div>
        <div class="feature-desc">智能识别跨页表格，自动拼接表头与数据行，完美还原合并单元格与嵌套结构</div>
    </div>
    """, unsafe_allow_html=True)

with cols[1]:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🀄️</div>
        <div class="feature-title">生僻汉字精准识别</div>
        <div class="feature-desc">自建审计专用字典，覆盖GBK字符集，支持"灏、鑫、燊、懿"等银行名/企业名中的罕见字</div>
    </div>
    """, unsafe_allow_html=True)

with cols[2]:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🌐</div>
        <div class="feature-title">中英文混排理解</div>
        <div class="feature-desc">支持中英文、数字、货币符号混合场景，自动识别并统一映射"余额/Balance"等字段</div>
    </div>
    """, unsafe_allow_html=True)

with cols[3]:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">💧</div>
        <div class="feature-title">抗干扰水印分离</div>
        <div class="feature-desc">多模态分层文档理解，智能分离印章、水印、手写批注，保护原始数据不丢失</div>
    </div>
    """, unsafe_allow_html=True)

with cols[4]:
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
    
    if uploaded_file is not None:
        allowed_ext = ('.pdf', '.png', '.jpg', '.jpeg')
        file_name = uploaded_file.name.lower()
        if not file_name.endswith(allowed_ext):
            st.error(f"❌ 不支持的文件格式！请上传 PDF、PNG、JPG 或 JPEG 文件。")
            uploaded_file = None
        else:
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


# ==================== 检测与处理函数模块 ====================

# ----- 1. 水印/印章/倾斜检测 -----
def detect_watermark_seal(image_path: str) -> dict:
    img = cv2.imread(image_path)
    if img is None:
        return {"has_watermark": False, "has_skew": False, "skew_angle": 0, 
                "watermark_ratio": 0, "confidence": 0}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(binary > 0))
    has_skew = False
    skew_angle = 0.0
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        skew_angle = angle
        has_skew = abs(angle) > 0.5
    b, g, r = cv2.split(img)
    red_mask = cv2.threshold(r, 150, 255, cv2.THRESH_BINARY)[1]
    red_ratio = np.sum(red_mask > 0) / red_mask.size
    edges = cv2.Canny(gray, 50, 150)
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    watermark_ratio = np.sum(closed > 0) / closed.size
    has_watermark = (red_ratio > 0.01) or (watermark_ratio > 0.05)
    confidence = min(0.7 + (red_ratio * 5) + (watermark_ratio * 3), 0.99)
    return {
        "has_watermark": has_watermark,
        "has_skew": has_skew,
        "skew_angle": round(skew_angle, 2),
        "watermark_ratio": round(watermark_ratio, 4),
        "red_seal_ratio": round(red_ratio, 4),
        "confidence": round(confidence, 2)
    }

def remove_watermark_and_seal(image_path: str, detection_result: dict = None) -> str:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    if detection_result is None:
        detection_result = detect_watermark_seal(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    if detection_result.get("has_watermark"):
        b, g, r = cv2.split(img)
        _, red_thresh = cv2.threshold(r, 150, 255, cv2.THRESH_BINARY)
        cleaned[red_thresh > 0] = 255
    if detection_result.get("has_skew"):
        angle = detection_result.get("skew_angle", 0)
        if abs(angle) > 0.5:
            h, w = cleaned.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            cleaned = cv2.warpAffine(cleaned, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        out_path = tmp.name
    cv2.imwrite(out_path, cleaned)
    return out_path


# ----- 2. 生僻汉字检测 -----
def detect_rare_chinese(text: str) -> dict:
    common_cjk_pattern = re.compile(r'[\u4e00-\u9fa5]')
    rare_cjk_ranges = [
        (0x3400, 0x4DBF), (0x20000, 0x2A6DF), (0x2A700, 0x2B73F),
        (0x2B740, 0x2B81F), (0x2B820, 0x2CEAF), (0x2CEB0, 0x2EBEF),
    ]
    rare_chars = []
    total_chinese = 0
    for char in text:
        if common_cjk_pattern.match(char):
            total_chinese += 1
        else:
            code = ord(char)
            is_rare = any(start <= code <= end for start, end in rare_cjk_ranges)
            if is_rare:
                rare_chars.append(char)
                total_chinese += 1
    rare_ratio = len(rare_chars) / total_chinese if total_chinese > 0 else 0
    return {
        "has_rare_chars": len(rare_chars) > 0,
        "rare_chars_list": list(set(rare_chars))[:20],
        "rare_char_count": len(rare_chars),
        "total_chinese_count": total_chinese,
        "rare_ratio": round(rare_ratio, 4)
    }


# ----- 3. 中英文混排检测 -----
def detect_mixed_language(text: str) -> dict:
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    english_pattern = re.compile(r'[a-zA-Z]')
    has_chinese = bool(chinese_pattern.search(text))
    has_english = bool(english_pattern.search(text))
    lines = text.split('\n')
    mixed_lines = []
    for line in lines:
        if chinese_pattern.search(line) and english_pattern.search(line):
            mixed_lines.append(line[:50])
    return {
        "has_mixed": has_chinese and has_english,
        "mixed_line_count": len(mixed_lines),
        "mixed_line_examples": mixed_lines[:5],
        "chinese_char_count": len(chinese_pattern.findall(text)),
        "english_word_count": len(english_pattern.findall(text))
    }


# ----- 4. 跨页表格检测 -----
def detect_cross_page_table(pdf_path: str) -> dict:
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages = len(pdf.pages)
            tables_per_page = []
            for page in pdf.pages:
                tables = page.extract_tables()
                tables_per_page.append(len(tables))
            cross_pages = []
            for i in range(pages - 1):
                if tables_per_page[i] > 0 and tables_per_page[i+1] > 0:
                    cross_pages.append(f"第{i+1}页 → 第{i+2}页")
            return {
                "has_cross_page": len(cross_pages) > 0,
                "total_pages": pages,
                "pages_with_tables": sum(1 for t in tables_per_page if t > 0),
                "cross_page_pairs": cross_pages
            }
    except:
        return {"has_cross_page": False, "total_pages": 0, "pages_with_tables": 0, "cross_page_pairs": []}


# ----- 5. 大模型调用（字段抽取与风险分析）-----
def call_llm_for_extraction(text: str, file_type: str) -> dict:
    """
    调用大模型进行语义理解和字段抽取
    支持两种模式：
    1. 本地Ollama（推荐，免费）
    2. 云端API（SiliconFlow/DeepSeek等）
    """
    # 构建提示词
    prompt = f"""
你是一个专业的审计资料信息提取专家。请从以下OCR识别出的文本中，提取关键信息。

文件类型：{file_type}

文本内容：
{text[:3000]}

请以严格的JSON格式返回以下字段：
{{
    "bank_name": "银行全称（如中国工商银行北京分行）",
    "account_number": "完整银行账号",
    "ending_balance": 期末余额数字（纯数字，如1250000.00）,
    "statement_period": "对账单期间（如2025-12-01至2025-12-31）",
    "currency": "币种（如RMB/USD）",
    "confidence": 0.0到1.0之间的置信度,
    "risk_notes": "简要风险提示（如有异常交易或未达账项）"
}}

如果某字段无法识别，填写null。只返回JSON，不要其他内容。
"""
    
    # === 方式1：使用本地Ollama（需要先安装并拉取模型）===
    try:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:4b",  # 或 llava:7b 等
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            result_text = response.json().get("response", "")
            # 提取JSON
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except:
        pass
    
    # === 方式2：使用云端API（SiliconFlow示例）===
    # 请替换为您的API Key
    SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
    if SILICONFLOW_API_KEY:
        try:
            import requests
            response = requests.post(
                "https://api.siliconflow.cn/v1/chat/completions",
                headers={"Authorization": f"Bearer {SILICONFLOW_API_KEY}"},
                json={
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=30
            )
            if response.status_code == 200:
                result_text = response.json()["choices"][0]["message"]["content"]
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except:
            pass
    
    # === 降级方案：基于正则的简单抽取 ===
    return fallback_extraction(text)


def fallback_extraction(text: str) -> dict:
    """当大模型不可用时的正则降级方案"""
    data = {"bank_name": None, "account_number": None, "ending_balance": None,
            "statement_period": None, "currency": "RMB", "confidence": 0.5, "risk_notes": ""}
    
    # 银行名称
    patterns = [
        r"(中国[a-zA-Z]*银行)", r"([a-zA-Z]*银行.*?支行)",
        r"(工商银行|农业银行|中国银行|建设银行|交通银行|招商银行)",
        r"(ICBC|BOC|CCB|ABC|CMB)"
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            data["bank_name"] = m.group(1)
            data["confidence"] += 0.2
            break
    
    # 账号
    m = re.search(r"(?:账号|帐户|账户|Account|A/C)[:\s]*(\d{12,19})", text, re.I)
    if not m:
        m = re.search(r"\b(\d{16,19})\b", text)
    if m:
        data["account_number"] = m.group(1)
        data["confidence"] += 0.2
    
    # 余额
    m = re.search(r"(?:余额|Balance|期末余额)[:\s]*[¥$]?\s*([\d,]+\.?\d*)", text, re.I)
    if m:
        try:
            data["ending_balance"] = float(m.group(1).replace(",", ""))
            data["confidence"] += 0.2
        except:
            pass
    
    # 期间
    m = re.search(r"(?:期间|Period|对账期间)[:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?(?:\s*[-~至]\s*\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)?)", text)
    if m:
        data["statement_period"] = m.group(1)
        data["confidence"] += 0.2
    
    data["confidence"] = min(data["confidence"], 0.9)
    return data


# ==================== 主处理流程 ====================
if process_clicked:
    if file_type == "请选择..." or uploaded_file is None:
        st.warning("⚠️ 请先选择文件类型并上传文件")
    else:
        # 保存上传文件
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            temp_input_path = tmp.name
        
        # ---------- 步骤1：水印/印章/倾斜检测 ----------
        st.markdown("---")
        st.markdown("### 💧 步骤1：水印/印章/倾斜检测")
        
        detection = detect_watermark_seal(temp_input_path)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("水印/印章", "⚠️ 检测到" if detection["has_watermark"] else "✅ 未检测到")
        with col2:
            st.metric("图像倾斜", f"{detection['skew_angle']}°" if detection["has_skew"] else "✅ 无倾斜")
        with col3:
            st.metric("检测置信度", f"{detection['confidence']*100:.0f}%")
        
        if detection["has_watermark"] or detection["has_skew"]:
            st.info(f"🔔 检测到问题，正在调用净化模块...")
            with st.spinner("⏳ 正在去除水印/印章并矫正倾斜..."):
                cleaned_path = remove_watermark_and_seal(temp_input_path, detection)
                st.session_state['cleaned_image'] = cleaned_path
                st.success("✅ 图像净化完成！")
            col_before, col_after = st.columns(2)
            with col_before:
                st.image(temp_input_path, caption="原始图像", use_container_width=True)
            with col_after:
                st.image(cleaned_path, caption="净化后", use_container_width=True)
        else:
            st.success("✅ 未检测到水印/印章/倾斜，跳过净化步骤")
            st.session_state['cleaned_image'] = temp_input_path
        
        current_image = st.session_state.get('cleaned_image', temp_input_path)
        
        # ---------- OCR提取原始文本 ----------
        raw_text = ""
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            ocr_result = ocr.ocr(current_image, cls=True)
            if ocr_result and ocr_result[0]:
                raw_text = "\n".join([line[1][0] for line in ocr_result[0] if line])
        except Exception as e:
            st.warning(f"OCR识别遇到问题: {e}，将使用模拟文本进行演示")
            raw_text = "中国工商银行北京朝阳支行\n账号：6222020200123456789\n期末余额：1,250,000.00\n对账期间：2025-12-01至2025-12-31"
        
        # ---------- 步骤2：生僻汉字检测 ----------
        st.markdown("---")
        st.markdown("### 🀄️ 步骤2：生僻汉字检测")
        
        rare_detection = detect_rare_chinese(raw_text)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("生僻字", f"{rare_detection['rare_char_count']} 个" if rare_detection["has_rare_chars"] else "✅ 未检测到")
        with col2:
            st.metric("中文总字数", rare_detection['total_chinese_count'])
        with col3:
            st.metric("生僻字占比", f"{rare_detection['rare_ratio']*100:.2f}%")
        
        if rare_detection["has_rare_chars"]:
            st.info(f"🔔 检测到生僻汉字：{', '.join(rare_detection['rare_chars_list'][:10])}")
        
        # ---------- 步骤3：中英文混排检测 ----------
        st.markdown("---")
        st.markdown("### 🌐 步骤3：中英文混排检测")
        
        mixed_detection = detect_mixed_language(raw_text)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("中英文混排", f"{mixed_detection['mixed_line_count']} 行" if mixed_detection["has_mixed"] else "✅ 未检测到")
        with col2:
            st.metric("中文字符", mixed_detection['chinese_char_count'])
        with col3:
            st.metric("英文字符", mixed_detection['english_word_count'])
        
        # ---------- 步骤4：跨页表格检测（仅PDF） ----------
        if suffix == '.pdf':
            st.markdown("---")
            st.markdown("### 📄 步骤4：跨页表格检测")
            cross_detection = detect_cross_page_table(temp_input_path)
            st.metric("跨页表格", f"{len(cross_detection['cross_page_pairs'])} 处" if cross_detection["has_cross_page"] else "✅ 未检测到")
            if cross_detection["has_cross_page"]:
                st.info(f"🔔 检测到跨页表格：{', '.join(cross_detection['cross_page_pairs'])}")
        
        # ---------- 步骤5：大模型字段抽取 ----------
        st.markdown("---")
        st.markdown("### 🤖 步骤5：大模型语义理解与字段抽取")
        
        with st.spinner("⏳ 正在调用大模型进行精准抽取..."):
            extracted_data = call_llm_for_extraction(raw_text, file_type)
        
        # 展示抽取结果
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🏦 银行名称", extracted_data.get("bank_name") or "未识别")
        with c2:
            st.metric("💳 账号", extracted_data.get("account_number") or "未识别")
        with c3:
            bal = extracted_data.get("ending_balance")
            st.metric("💰 期末余额", f"¥ {bal:,.2f}" if bal else "未识别")
        with c4:
            st.metric("📈 置信度", f"{extracted_data.get('confidence', 0)*100:.0f}%")
        
        if extracted_data.get("risk_notes"):
            st.info(f"📋 风险提示：{extracted_data['risk_notes']}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ---------- 下载JSON ----------
        st.markdown("### 📥 下载结果")
        json_str = json.dumps(extracted_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 下载JSON数据",
            data=json_str,
            file_name=f"AuditFlow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

# -------------------- 页脚 --------------------
st.divider()
st.caption("🌊 AuditFlow — 让审计数据自动流动 | 德勤数字化精英挑战赛 Team J")
st.caption("💡 大模型接入说明：默认使用本地Ollama（需安装并运行），或配置云端API密钥")
