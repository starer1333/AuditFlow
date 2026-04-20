import os
import json
from config import OUTPUT_DIR
from modules.file_handler import detect_format, pdf_to_images, extract_tables_from_pdf, tables_to_excel, get_input_files
from modules.image_cleaner import clean_image
from modules.ocr_engine import ocr_image
from modules.llm_extractor import extract_with_llm, fuse_results
from modules.field_validator import validate
from modules.excel_generator import generate

def process_file(file_path):
    print(f"\n处理: {os.path.basename(file_path)}")
    ftype, scanned = detect_format(file_path)
    print(f"[痛点1、5] 文件类型: {ftype}, 扫描件: {scanned}")
    if ftype == 'pdf':
        tables = extract_tables_from_pdf(file_path)
        if tables:
            p = tables_to_excel(tables)
            print(f"[痛点1、5] 表格提取重建: {p}")
        images = pdf_to_images(file_path)
        work_img = images[0]
    else:
        work_img = file_path
    cleaned = clean_image(work_img)
    print(f"[痛点4] 图像净化完成")
    _, ocr_fields = ocr_image(cleaned)
    print(f"[痛点2、3] OCR完成，置信度: {ocr_fields.get('confidence',0)*100:.0f}%")
    llm_fields = extract_with_llm(cleaned, ocr_fields)
    if llm_fields:
        print("[大模型] 二次识别完成")
    fused = fuse_results(ocr_fields, llm_fields)
    fused = validate(fused)
    print(f"[校验] 最终置信度: {fused['validation']['final_confidence']*100:.0f}%")
    excel_path = generate(fused)
    print(f"[输出] Excel底稿: {excel_path}")
    with open(os.path.join(OUTPUT_DIR, "fused_data.json"), "w", encoding="utf-8") as f:
        json.dump(fused, f, ensure_ascii=False, indent=2)

def main():
    files = get_input_files()
    if not files:
        print("请将文件放入 inputs 文件夹")
        return
    selected = files[0] if len(files)==1 else files[int(input("选择序号: "))-1]
    process_file(selected)

if __name__ == "__main__":
    main()