import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED_FORMATS = ('.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff')

# 硅基流动 API（免费注册获取）
SILICONFLOW_API_KEY = "sk-your-api-key-here"  # 请替换为您的真实Key
LLM_MODEL = "Qwen/Qwen2-VL-72B-Instruct"