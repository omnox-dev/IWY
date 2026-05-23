import cv2
from ultralytics import YOLO
import time
import threading
try:
    import winsound
    HAVE_WINSOUND = True
except Exception:
    HAVE_WINSOUND = False

def beep_alert(level='short'):
    """Non-blocking beep patterns. level: 'short' or 'urgent'"""
    def _do_beep():
        if HAVE_WINSOUND:
            try:
                if level == 'urgent':
                    # three short beeps
                    winsound.Beep(1200, 150)
                    time.sleep(0.05)
                    winsound.Beep(1400, 150)
                    time.sleep(0.05)
                    winsound.Beep(1600, 180)
                else:
                    winsound.Beep(1000, 180)
            except Exception:
                print("[BEEP]")
        else:
            if level == 'urgent':
                print("[BEEP URGENT]")
            else:
                print("[BEEP]")
    threading.Thread(target=_do_beep, daemon=True).start()

from ocr import read_text_from_roi
from tts_queue import speak


def start_vision_system():
    # --- CAMERA CONFIGURATION ---
    CAMERA_SOURCE = 0 
    
    # Load the YOLOv8 Nano model
    model = YOLO("yolov8n.pt")
    
    # Initialize webcam capture
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Warm up camera and get dimensions
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read from webcam.")
        return
    h, w = frame.shape[:2]

    # Pre-calculate OCR ROI (Center of screen)
    rw_ocr = int(w * 0.6)
    rh_ocr = int(h * 0.25)
    x_ocr = int((w - rw_ocr) / 2)
    y_ocr = int((h - rh_ocr) / 2)

    # State variables for new gesture system
    system_active = True
    is_ocr_mode = False
    action_requested = None
    last_tap_time = 0.0
    single_tap_timer = None
    
    # HUD & Bounding Box State
    current_boxes = []
    boxes_clear_time = 0.0
    last_spoken_text = "System Ready"
    
    # Auto-scan configuration (disabled, manual only)
    last_scan_time = 0
    scan_interval = 5.0
    spoken_cache = {}
    spoken_cache_ttl = 8.0

    print("Vision System Loaded. Double click to change mode. Single click to scan.")
    speak("System ready. Double tap anywhere to switch mode. Tap once for status.", priority=1, rate=150)

    def mouse_callback(event, x, y, flags, param):
        nonlocal last_tap_time, single_tap_timer, is_ocr_mode, action_requested
        
        if event == cv2.EVENT_LBUTTONDOWN:
            # Single click detected - wait briefly to verify it's not a double click
            def single_click_action():
                nonlocal action_requested
                action_requested = 'ocr' if is_ocr_mode else 'quick_scan'
                
            single_tap_timer = threading.Timer(0.35, single_click_action)
            single_tap_timer.start()
            
        elif event == cv2.EVENT_LBUTTONDBLCLK:
            # Native double click detected
            if single_tap_timer:
                single_tap_timer.cancel()
            is_ocr_mode = not is_ocr_mode
            mode_str = "Reading mode" if is_ocr_mode else "Safety mode"
            speak(mode_str, priority=1, rate=160)
            print(f"[GESTURE] Double Tap -> {mode_str}")

    cv2.namedWindow("Vision Assistant")
    cv2.setMouseCallback("Vision Assistant", mouse_callback)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()

        # Handle requested gestures (Single Tap Actions)
        if action_requested:
            snapshot = frame.copy()
            if action_requested == 'quick_scan':
                print("[GESTURE] Single Tap -> Quick scan requested")
                def quick_scan():
                    nonlocal current_boxes, boxes_clear_time, last_spoken_text
                    try:
                        results_quick = model(snapshot, stream=False, conf=0.30)
                        object_counts = {}
                        boxes_to_draw = []
                        
                        for r in results_quick:
                            for box in r.boxes:
                                x1, y1, x2, y2 = box.xyxy[0].tolist()
                                cls = int(box.cls[0].item())
                                label = model.names[cls] if hasattr(model, 'names') else str(cls)
                                
                                boxes_to_draw.append((int(x1), int(y1), int(x2), int(y2), label))
                                
                                box_area = (x2 - x1) * (y2 - y1)
                                frame_area = w * h
                                area_ratio = box_area / frame_area
                                
                                centerX = x1 + (x2 - x1) / 2
                                pos_ratio = centerX / w
                                
                                distance = "far"
                                if area_ratio > 0.35:
                                    distance = "very close"
                                elif area_ratio > 0.15:
                                    distance = "near"
                                    
                                direction = "in the center"
                                if pos_ratio < 0.35:
                                    direction = "on your left"
                                elif pos_ratio > 0.65:
                                    direction = "on your right"
                                    
                                if label not in object_counts:
                                    object_counts[label] = {"count": 0, "details": []}
                                object_counts[label]["count"] += 1
                                object_counts[label]["details"].append(f"{distance} {direction}")
                        
                        current_boxes = boxes_to_draw
                        boxes_clear_time = time.time() + 6.0
                                
                        if object_counts:
                            description_parts = []
                            for obj, data in object_counts.items():
                                if data["count"] == 1:
                                    description_parts.append(f"one {obj} {data['details'][0]}")
                                else:
                                    description_parts.append(f"{data['count']} {obj}s, including one {data['details'][0]}")
                            
                            final_desc = "I see " + " and ".join(description_parts) + "."
                            last_spoken_text = final_desc
                            speak(final_desc, priority=1, rate=150)
                            print(f"[SCAN RESULT] {final_desc}")
                        else:
                            last_spoken_text = "No clear objects detected."
                            speak("No clear objects detected.", priority=1, rate=150)
                            print("[SCAN RESULT] No objects detected.")
                    except Exception as e:
                        print(f"Quick detection error: {e}")
                threading.Thread(target=quick_scan, daemon=True).start()
                
            elif action_requested == 'ocr':
                print("[GESTURE] Single Tap -> OCR Read requested")
                speak("Scanning text", priority=1, rate=160)
                
                last_spoken_text = "Analyzing text..."
                speak("Analyzing", priority=1, rate=150)
                def bg_worker(snap):
                    nonlocal last_spoken_text
                    txt2, conf2 = read_text_from_roi(snap, roi=(x_ocr, y_ocr, rw_ocr, rh_ocr), save_debug=False, fast=False)
                    if txt2:
                        last_spoken_text = f"Found: {txt2}"
                        speak(f"Text is: {txt2}", priority=1, rate=150)
                    else:
                        last_spoken_text = "No clear text found."
                        speak("No clear text found.", priority=1, rate=150)
                threading.Thread(target=bg_worker, args=(snapshot,), daemon=True).start()
            
            action_requested = None




        # Render UI
        ui_frame = frame.copy()

        # Apply dark overlay to simulate scanner look (Edge Enhancement Boost)
        overlay = ui_frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        alpha = 0.6 if is_ocr_mode else 0.3
        cv2.addWeighted(overlay, alpha, ui_frame, 1 - alpha, 0, ui_frame)

        NEON_YELLOW = (0, 234, 234) # BGR
        
        # Draw bounding boxes if active
        if time.time() < boxes_clear_time:
            for bx1, by1, bx2, by2, blabel in current_boxes:
                # Draw neon yellow box
                cv2.rectangle(ui_frame, (bx1, by1), (bx2, by2), NEON_YELLOW, 2)
                # Draw label background
                cv2.rectangle(ui_frame, (bx1, by1 - 18), (bx1 + len(blabel)*9 + 6, by1), NEON_YELLOW, -1)
                # Draw text
                cv2.putText(ui_frame, blabel.upper(), (bx1 + 3, by1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

        # Mode Indicator (HUD Top Bar)
        mode_text = "TEXT SCAN (OCR)" if is_ocr_mode else "EDGE-ENHANCEMENT"
        cv2.putText(ui_frame, mode_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, NEON_YELLOW, 2, cv2.LINE_AA)

        # Draw HUD Central Reticle
        cx, cy = w // 2, h // 2
        cv2.circle(ui_frame, (cx, cy), 60, (0, 100, 100), 1, cv2.LINE_AA)
        cv2.line(ui_frame, (cx - 15, cy), (cx + 15, cy), NEON_YELLOW, 1)
        cv2.line(ui_frame, (cx, cy - 15), (cx, cy + 15), NEON_YELLOW, 1)

        # Bottom Status Bar (Glassmorphism effect)
        overlay2 = ui_frame.copy()
        hud_h = 70
        cv2.rectangle(overlay2, (0, h - hud_h), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay2, 0.7, ui_frame, 0.3, 0, ui_frame)
        
        # Bottom Instructions & TTS Readout
        # Truncate text if too long
        display_text = last_spoken_text if len(last_spoken_text) < 70 else last_spoken_text[:67] + "..."
        cv2.putText(ui_frame, f"STATUS: {display_text}", (20, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(ui_frame, "DOUBLE-CLICK: Switch Mode | SINGLE-CLICK: Scan", (20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, NEON_YELLOW, 1, cv2.LINE_AA)
        # Bottom Instructions & TTS Readout

        cv2.imshow("Vision Assistant", ui_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys
    print(f"System starting with interpreter: {sys.executable}")
    start_vision_system()
