import os
import magic
import pdfplumber
from pdf2image import convert_from_path
from config import INPUT_DIR, OUTPUT_DIR, SUPPORTED_FORMATS
import pandas as pd

def detect_format(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"不支持的文件格式: {ext}")
    if ext == '.pdf':
        with pdfplumber.open(file_path) as pdf:
            text = "".join(p.extract_text() or "" for p in pdf.pages[:3])
        is_scanned = len(text.strip()) < 200
        return 'pdf', is_scanned
    return 'image', False

def pdf_to_images(pdf_path):
    images = convert_from_path(pdf_path, dpi=200)
    img_paths = []
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for i, img in enumerate(images):
        p = os.path.join(OUTPUT_DIR, f"{base}_page{i+1}.png")
        img.save(p, "PNG")
        img_paths.append(p)
    return img_paths

def extract_tables_from_pdf(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        pending = None
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table: continue
                cleaned = [[str(c).strip() if c else '' for c in row] for row in table]
                if pending and len(pending[-1]) == len(cleaned[0]):
                    pending.extend(cleaned[1:])
                    continue
                if pending: tables.append(pending)
                pending = cleaned
        if pending: tables.append(pending)
    return tables

def tables_to_excel(tables, name="extracted_tables.xlsx"):
    if not tables: return None
    path = os.path.join(OUTPUT_DIR, name)
    with pd.ExcelWriter(path) as w:
        for i, t in enumerate(tables):
            pd.DataFrame(t[1:], columns=t[0]).to_excel(w, sheet_name=f"Table_{i+1}", index=False)
    return path

def get_input_files():
    return [os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR) if f.lower().endswith(SUPPORTED_FORMATS)]