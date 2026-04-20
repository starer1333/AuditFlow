import cv2
import numpy as np
import os
from config import OUTPUT_DIR

def clean_image(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    coords = np.column_stack(np.where(cleaned > 0))
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.5:
            h, w = cleaned.shape[:2]
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            cleaned = cv2.warpAffine(cleaned, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    out = os.path.join(OUTPUT_DIR, "cleaned_image.png")
    cv2.imwrite(out, cleaned)
    return out