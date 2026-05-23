import cv2
import numpy as np
import re
import os
from dotenv import load_dotenv
from google import genai
from PIL import Image

# Load environment variables from .env file
load_dotenv()

# Configure Gemini API Client
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("WARNING: GEMINI_API_KEY environment variable not set. OCR will fail.")
    client = None

def read_text_from_roi(frame, roi=None, whitelist=None, save_debug=False, fast=False):
    """
    Extracts text from the full camera frame using Google Gemini 2.5 Flash API.
    (roi argument is kept for compatibility but ignored to use the full frame)
    """
    if not client:
        return "API key missing. Cannot read text.", -999

    if frame.size == 0:
        return "", -999

    # Convert full OpenCV image (BGR) to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL Image
    pil_img = Image.fromarray(rgb_frame)

    if save_debug:
        import time
        os.makedirs('snapshots', exist_ok=True)
        ts = int(time.time() * 1000)
        cv2.imwrite(f'snapshots/ocr_gemini_{ts}.png', frame)

    try:
        # Send image to Gemini with a specific prompt
        prompt = "Extract all text visible in this image accurately. Return only the extracted text, nothing else."
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, pil_img]
        )
        
        text = response.text.strip() if response.text else ""
        
        # Clean text slightly (Gemini usually does a good job, but just to be safe)
        text = re.sub(r'[^a-zA-Z0-9\s\.\!\?\,\:\;\-\(\)\']', '', text)
        text = " ".join(text.split())
        
        if len(text) > 0:
            text = text[0].upper() + text[1:]
            if text[-1] not in '.!?':
                text = text + '.'
                
        # We assume high confidence if we get a valid string back.
        confidence = 100 if text else 0
        
        print(f"[OCR Gemini Output]: '{text}'")
        return text, confidence
        
    except Exception as e:
        print(f"[OCR Gemini Error]: {e}")
        return "", -999
