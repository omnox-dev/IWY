# AI-Based Voice Assistance System for Visually Impaired Patients - Phase I

## Overview
This project aims to develop a real-time "Vision-to-Audio" assistance system for visually impaired individuals, specifically those with Glaucoma. Phase I focuses on a laptop-based prototype to validate the core logic and latency.

## Implementation Strategy

### Module 1: Environmental Setup
- [x] Install Python 3.9+.
- [x] Create a virtual environment: `python -m venv glauc_env`.
- [x] Install dependencies:
  - `ultralytics` (YOLOv8)
  - `opencv-python`
  - `pytesseract`
  - `pyttsx3`
- [x] Verify GDAL/Tesseract installation on the system.

### Module 2: The Vision Pipeline (YOLO)
- [x] Implement `cv2.VideoCapture(0)` for webcam access.
- [x] Load pre-trained YOLOv8 weights (`yolov8n.pt`).
- [x] Implement a frame processing loop (processing every Nth frame).
- [x] Add proximity logic (trigger alert if object area > 40% of screen).

### Module 3: The Reading Pipeline (OCR)
- [x] Implement Region of Interest (ROI) trigger.
- [x] Image preprocessing: Grayscale -> Thresholding -> Denoising.
- [x] Integrate PyTesseract for text extraction.
- [x] Implement string filtering and confidence checks.

### Module 4: The Voice Integration (TTS)
- [x] Initialize `pyttsx3` engine.
- [x] Configure voice rates for different alert types (Hazards vs. Reading).
- [x] **Crucial**: Implement TTS in a separate daemon thread to prevent UI freezing.

## Tech Stack
- **Language**: Python 3.9+
- **Vision**: OpenCV
- **AI Models**: Ultralytics YOLOv8, Pytesseract
- **Audio**: Pyttsx3 (Offline)

## Success Criteria
- Real-time performance with latency < 200ms.
- High confidence object detection for hazards (person, car, chair, stairs).
- Reliable OCR for high-contrast signage.
- Asynchronous audio feedback without video lag.
