"""
阶段二：格式检测与图像净化（对应第一、二道关卡）
运行：python step2_format_and_clean.py
"""
import os
import magic
import pdfplumber
import cv2
import numpy as np
from pdf2image import convert_from_path

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPPORTED = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff'}


def clean_image(img_path):
    """
    图像净化：灰度、去噪、二值化（抑制浅色水印）、倾斜矫正
    对应流程图中第二道关卡的全部步骤
    """
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 高斯模糊去噪
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # 自适应阈值二值化（有效抑制水印、背景纹理）
    binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    # 形态学闭运算去除小噪点
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # 倾斜矫正（基于最小外接矩形）
    coords = np.column_stack(np.where(cleaned > 0))
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.5:
            h, w = cleaned.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            cleaned = cv2.warpAffine(cleaned, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    out_path = os.path.join(OUTPUT_DIR, "cleaned_image.png")
    cv2.imwrite(out_path, cleaned)
    return out_path


def main():
    print("=" * 50)
    print("阶段二：格式检测与图像净化")
    print("=" * 50)

    files = [f for f in os.listdir(INPUT_DIR) if os.path.splitext(f)[1].lower() in SUPPORTED]
    if not files:
        print(f"❌ 请在 inputs 文件夹放入支持的文件: {SUPPORTED}")
        input("\n按回车退出...")
        return

    # 选择文件
    if len(files) == 1:
        f = files[0]
    else:
        for i, name in enumerate(files, 1):
            print(f"[{i}] {name}")
        idx = int(input(f"选择序号(1-{len(files)}): ").strip() or 1) - 1
        f = files[idx]

    file_path = os.path.join(INPUT_DIR, f)
    ext = os.path.splitext(f)[1].lower()
    print(f"\n处理文件: {f}")

    # 第一道关卡：格式检测
    mime = magic.from_file(file_path, mime=True)
    print(f"MIME类型: {mime}")

    work_image = None
    if ext == '.pdf':
        with pdfplumber.open(file_path) as pdf:
            text = "".join(p.extract_text() or "" for p in pdf.pages[:3])
        if len(text.strip()) < 200:  # 扫描件PDF
            print("检测为扫描件PDF，转换为图片...")
            images = convert_from_path(file_path, dpi=200)
            work_image = os.path.join(OUTPUT_DIR, "pdf_page1.png")
            images[0].save(work_image, "PNG")
        else:
            print("❌ 电子PDF暂不支持，请使用扫描件或图片")
            return
    else:
        work_image = file_path

    if work_image:
        print("正在进行图像净化（去噪/二值化/倾斜矫正/水印抑制）...")
        cleaned = clean_image(work_image)
        print(f"✅ 净化完成: {cleaned}")
        print("\n请打开 outputs 文件夹查看 cleaned_image.png，确认文字清晰、水印被抑制。")

    print("=" * 50)
    print("✅ 阶段二完成，可运行阶段三。")
    input("\n按回车退出...")


if __name__ == "__main__":
    main()