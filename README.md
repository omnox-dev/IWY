# IWY - Glaucoma Helping Tool

IWY (I Watch for You) is a screen capture/camera-based vision assistant designed to help visually impaired individuals, specifically focusing on those with Glaucoma. The system provides real-time object detection and OCR (Optical Character Recognition) via voice feedback.

## Features
- **Real-time Object Detection:** Uses YOLOv8 Nano to detect common objects in the environment.
- **OCR (Text-to-Speech):** Extracts text from the center of the viewport and reads it aloud using `pyttsx3`.
- **Intelligent Beep System:** Provides non-blocking audio cues for urgent objects or general awareness.
- **Prioritized TTS Queue:** Managed voice feedback that handles interruptions and priority messages.

---

## Setup Guide

### 1. Prerequisites
- **Python 3.8 - 3.12** is recommended.
- **Tesseract OCR Engine:** Required for the OCR functionality.
  - **Windows:** Download and install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki). Add the installation path (usually `C:\Program Files\Tesseract-OCR`) to your system environment variables.
  - **Linux:** `sudo apt install tesseract-ocr`
  - **macOS:** `brew install tesseract`

### 2. Installation
1. Clone or download this repository.
2. Open a terminal in the project directory.
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Running the Tool
Launch the main application by running:
```bash
python main.py
```

### 4. Using your Mobile Camera
You can use your smartphone as a high-quality camera for this system:

#### Option A: WiFi/USB (Easiest)
1. Install **DroidCam** or **iVCam** on both your phone and PC.
2. Connect them via WiFi or USB.
3. In [main.py](main.py), change `CAMERA_SOURCE = 0` to `1` or `2` (the index of the virtual camera).

#### Option B: IP Camera (WiFi)
1. Install an "IP Webcam" app on your phone and start the server.
2. In [main.py](main.py), change `CAMERA_SOURCE` to the URL provided by the app (e.g., `CAMERA_SOURCE = "http://192.168.1.5:8080/video"`).

### 5. Controls
- **'s' Key:** Start/Stop the vision monitoring system.
- **'r' Key:** Trigger immediate OCR (reads text in the center box).
- **'q' Key:** Quit the application.

---

## Project Structure
- `main.py`: The entry point and main loop for vision and interaction.
- `ocr.py`: Handles image preprocessing and Tesseract OCR integration.
- `tts_queue.py`: A prioritized, thread-safe queue for text-to-speech output.
- `yolov8n.pt`: YOLOv8 Nano pre-trained weights.
- `plan.md`: The development roadmap and technical notes.
