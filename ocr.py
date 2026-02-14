import cv2
import pytesseract
import numpy as np
import re

def _run_tesseract_and_confidence(img, psm=3, whitelist=None):
    cfg = f'--oem 3 --psm {psm}'
    if whitelist:
        cfg += f" -c tessedit_char_whitelist={whitelist}"
    try:
        data = pytesseract.image_to_data(img, config=cfg, output_type=pytesseract.Output.DICT)
    except Exception:
        return "", -999
    confs = []
    texts = []
    for i, t in enumerate(data.get('text', [])):
        txt = str(t).strip()
        if txt:
            try:
                c = float(data['conf'][i])
            except:
                c = -1.0
            confs.append(c)
            texts.append(txt)
    if len(confs) == 0:
        return "", -999
    avg_conf = sum(confs) / len(confs)
    return " ".join(texts), avg_conf

def _adjust_gamma(image, gamma=1.0):
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
                        for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

# Preprocess an ROI and return extracted text
def read_text_from_roi(frame, roi=None, whitelist=None, save_debug=False, fast=False):
    # If roi provided as (x,y,w,h) crop, else use center region
    h, w = frame.shape[:2]
    if roi:
        x, y, rw, rh = roi
        # Clip ROI to frame boundaries
        x, y = max(0, x), max(0, y)
        rw, rh = min(w - x, rw), min(h - y, rh)
        crop = frame[y:y+rh, x:x+rw]
    else:
        # centered ROI (60% width, 25% height)
        rw = int(w * 0.6)
        rh = int(h * 0.25)
        x = int((w - rw) / 2)
        y = int((h - rh) / 2)
        crop = frame[y:y+rh, x:x+rw]

    if crop.size == 0:
        return "", -999

    # Quick fast path for low latency: simple preprocessing and quick psm
    def _fast_ocr(crop_img):
        gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.convertScaleAbs(gray, alpha=1.4, beta=10)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if cv2.countNonZero(th) < th.size / 2:
            th = cv2.bitwise_not(th)
        th = cv2.medianBlur(th, 3)
        th = cv2.resize(th, (th.shape[1]*2, th.shape[0]*2), interpolation=cv2.INTER_LANCZOS4)
        t, conf = _run_tesseract_and_confidence(th, psm=6, whitelist=whitelist)
        # Simple cleanup
        t = re.sub(r'[^a-zA-Z0-9\s\.\!\?]', '', t)
        t = " ".join(t.split())
        if len(t) > 0:
            t = t[0].upper() + t[1:]
            if t[-1] not in '.!?':
                t = t + '.'
        return t, conf

    if fast:
        return _fast_ocr(crop)

    # Ensemble preprocessing: create multiple variants and pick best OCR result

    # Create multiple preprocessing variants including low-light enhancements
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    variants = {}

    # Variant 1: Max channel + CLAHE (bright colored text on dark bg)
    b, g, r = cv2.split(crop)
    maxc = cv2.max(cv2.max(b, g), r)
    v1 = clahe.apply(maxc)
    v1 = cv2.fastNlMeansDenoising(v1, None, h=10)
    v1 = cv2.GaussianBlur(v1, (3, 3), 0)
    variants['maxc_clahe_denoise'] = v1

    # Variant 2: Gray + CLAHE
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    v2 = clahe.apply(gray)
    v2 = cv2.fastNlMeansDenoising(v2, None, h=8)
    variants['gray_clahe_denoise'] = v2

    # Variant 3: HSV value channel equalized (helps low-light colored text)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hch, sch, vch = cv2.split(hsv)
    vch = clahe.apply(vch)
    vch = cv2.fastNlMeansDenoising(vch, None, h=8)
    variants['hsv_value_clahe'] = vch

    # Variant 4: Gamma corrected brightening (for very dark scenes)
    v4 = _adjust_gamma(gray, gamma=0.6)  # brighten (gamma <1 brightens darks)
    v4 = clahe.apply(v4)
    variants['gamma_bright'] = v4

    # Variant 5: Sharpened gray (for thin fonts)
    kernel_sharp = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
    v5 = cv2.filter2D(v2, -1, kernel_sharp)
    variants['sharpen'] = v5

    processed_images = {}
    for name, img in variants.items():
        # Ensure image is single channel grayscale
        if len(img.shape) == 3:
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = img

        # Try both Otsu and adaptive thresholding (different block sizes)
        try:
            _, th_otsu = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        except Exception:
            th_otsu = img_gray
        th_adapt1 = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 21, 5)
        th_adapt2 = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                          cv2.THRESH_BINARY, 15, 7)

        candidates = {'otsu': th_otsu, 'adapt1': th_adapt1, 'adapt2': th_adapt2}
        for cname, th in candidates.items():
            # Auto-invert if background is dark
            white_pixels = cv2.countNonZero(th)
            total_pixels = th.shape[0] * th.shape[1]
            if white_pixels < total_pixels / 2:
                th = cv2.bitwise_not(th)
            # Small morphology to clean noise and fill gaps
            th = cv2.medianBlur(th, 3)
            kernel = np.ones((2, 2), np.uint8)
            th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
            th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
            # Optional dilation to thicken thin text
            th_dil = cv2.dilate(th, np.ones((2,2), np.uint8), iterations=1)
            # Increase effective DPI for tesseract
            scale = 4
            try:
                processed_images[f"{name}_{cname}"] = cv2.resize(th, (th.shape[1]*scale, th.shape[0]*scale), interpolation=cv2.INTER_LANCZOS4)
                processed_images[f"{name}_{cname}_dil"] = cv2.resize(th_dil, (th_dil.shape[1]*scale, th_dil.shape[0]*scale), interpolation=cv2.INTER_LANCZOS4)
            except Exception:
                processed_images[f"{name}_{cname}"] = th
                processed_images[f"{name}_{cname}_dil"] = th_dil

    psm_list = [6, 7, 3]
    best = ("", -999, None, None)
    for img_name, img in processed_images.items():
        for psm in psm_list:
            t, conf = _run_tesseract_and_confidence(img, psm=psm, whitelist=whitelist)
            if conf > best[1] or (conf == best[1] and len(t) > len(best[0])):
                best = (t, conf, psm, img_name)

    # Optionally save debug snapshot
    if save_debug:
        import os, time
        os.makedirs('snapshots', exist_ok=True)
        ts = int(time.time() * 1000)
        if best[3] in processed_images:
            cv2.imwrite(f'snapshots/ocr_best_{ts}_{best[2]}_{best[3]}.png', processed_images[best[3]])

    if best[3] in processed_images:
        cv2.imshow("OCR Debug - What AI Sees", processed_images[best[3]])
        cv2.waitKey(1)

    text = best[0]

    # Clean text: remove non-alphanumeric (keep spaces and simple punctuation)
    text = re.sub(r'[^a-zA-Z0-9\s\.\!\?]', '', text)
    text = " ".join(text.split())
    # Simple post-processing to make TTS read more fluently:
    if len(text) > 0:
        # Capitalize first character and ensure sentence ends with punctuation
        text = text[0].upper() + text[1:]
        if text[-1] not in '.!?':
            text = text + '.'

    print(f"[OCR Raw Output]: '{text}' (conf={best[1]:.1f}, psm={best[2]}, variant={best[3]})")
    return text.strip(), best[1]
