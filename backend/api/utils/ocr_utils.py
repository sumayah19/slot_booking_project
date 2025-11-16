import re
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import os
from django.conf import settings

def preprocess_image(image_path):
    img = Image.open(image_path).convert('L')
    img = ImageOps.invert(img)
    img = img.filter(ImageFilter.MedianFilter())
    w,h = img.size
    img = img.resize((int(w*1.5), int(h*1.5)))
    return img

def extract_plate_text(image_path):
    try:
        img = preprocess_image(image_path)
        txt = pytesseract.image_to_string(img, config='--psm 7')  # single line
        txt = re.sub(r'[^A-Za-z0-9 ]','', txt).strip().upper()
        # Indian plate heuristic: look for patterns like KA01AB1234 or KA 01 AB 1234
        m = re.search(r'[A-Z]{2}\s*\d{1,2}\s*[A-Z]{0,3}\s*\d{1,4}', txt)
        if m:
            return re.sub(r'\s+','', m.group(0))
        if txt:
            return txt.replace(' ','')
    except Exception as e:
        # fallback - stub
        return None
    return None
