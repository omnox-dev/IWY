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
    # Load the YOLOv8 Nano model (Module 2)
    model = YOLO("yolov8n.pt")
    
    # Initialize webcam capture
    cap = cv2.VideoCapture(0)
    
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

    print("Vision System Loaded. Press 's' to start monitoring.")
    speak("System ready. Press S to start monitoring.", priority=1, rate=150)

    system_active = False # New flag to prevent immediate start
    frame_count = 0
    process_nth_frame = 3  # Performance optimization: process every 3rd frame
    last_spoken = 0
    speak_cooldown = 1.0  # seconds between TTS messages to avoid flooding
    # Auto-scan mode state
    scan_active = False
    last_scan_time = 0
    scan_interval = 5.0  # seconds between automatic scans
    spoken_cache = {}  # label string -> last spoken time
    spoken_cache_ttl = 8.0  # increased TTL to match longer interval
    last_key_time = 0 # Debounce timer

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Periodic automatic scan when enabled (non-blocking)
        # This is where we do the 3-second cycle detection and beep logic.
        # This fixes the "bombardment" and crash by running detection only once in a controlled way.
        now = time.time()
        if system_active and (now - last_scan_time) >= scan_interval:
            last_scan_time = now
            snap = frame.copy()
            
            def auto_scan_worker(snap_img):
                try:
                    # Run model on the snap
                    results_auto = model(snap_img, stream=True, conf=0.45)
                    labels = []
                    found_urgent = False
                    
                    # Double check if system was turned off while processing started
                    if not system_active: return

                    for r in results_auto:
                        for box in r.boxes:
                            if not system_active: return
                            x1, y1, x2, y2 = box.xyxy[0]
                            cls = int(box.cls[0])
                            label = model.names[cls] if hasattr(model, 'names') else str(cls)
                            labels.append(label)
                            
                            # Proximity Check Logic (Urgent)
                            box_area = (x2 - x1) * (y2 - y1)
                            frame_area = w * h
                            area_percentage = (box_area / frame_area) * 100
                            
                            if area_percentage > 40:
                                # Urgent obstacle alert
                                beep_alert('urgent')
                                speak(f"Urgent: {label} very close", priority=1, rate=210)
                                found_urgent = True
                                break # Prioritize one urgent alert per scan

                    if not system_active: return

                    if labels and not found_urgent:
                        # General description if no urgent obstacle
                        unique = list(dict.fromkeys(labels))
                        labels_str = ", ".join(unique)
                        
                        # Use cache to avoid repeating same objects every 3s if they are static
                        last_sp = spoken_cache.get(labels_str, 0)
                        if time.time() - last_sp > spoken_cache_ttl:
                            spoken_cache[labels_str] = time.time()
                            speak(f"Objects: {labels_str}", priority=4, rate=150)
                    
                except Exception as e:
                    print(f"Auto-scan error: {e}")

            threading.Thread(target=auto_scan_worker, args=(snap,), daemon=True).start()

        # Show system status
        status_text = "MONITORING ACTIVE" if system_active else "SYSTEM STANDBY - PRESS 'S'"
        status_color = (0, 255, 0) if system_active else (0, 255, 255)
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        # Draw OCR Guide Box
        cv2.rectangle(frame, (x_ocr, y_ocr), (x_ocr + rw_ocr, y_ocr + rh_ocr), (255, 255, 0), 2)
        cv2.putText(frame, "Align Text Here (Press 'R')", (x_ocr, y_ocr - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # Show the output frame
        cv2.imshow("Vision Assistance System - Phase I", frame)

        key = cv2.waitKey(1) & 0xFF
        # Handle keypresses (case-insensitive)
        if key == ord('q') or key == ord('Q'):
            break

        # Toggle system active / monitoring mode
        if (key == ord('s') or key == ord('S')) and (time.time() - last_key_time > 0.5):
            last_key_time = time.time()
            system_active = not system_active
            scan_active = system_active 
            state = "started" if system_active else "stopped"
            print(f"[KEY] 'S' pressed - System {state}")
            
            # Use priority 2 for status messages (can interrupt lower descriptions, but interrupted by urgent)
            # When stopping, we use priority 1 (urgent) to clear the queue and stop speaking immediately
            prio = 1 if not system_active else 2
            speak(f"System monitoring {state}", priority=prio, rate=160)
            
            if system_active:
                last_scan_time = time.time()
        
        # What is in front...
        if key == ord('w') or key == ord('W'):
            # Force urgent priority to override background scans
            print("[KEY] 'W' pressed - Quick scan requested")
            snapshot = frame.copy()
            # Run quick scan in a separate thread to avoid UI freezing
            def quick_scan():
                try:
                    results_quick = model(snapshot, stream=True, conf=0.45)
                    labels = []
                    for r in results_quick:
                        for box in r.boxes:
                            cls = int(box.cls[0])
                            label = model.names[cls] if hasattr(model, 'names') else str(cls)
                            labels.append(label)
                    
                    if labels:
                        labels_str = ", ".join(dict.fromkeys(labels))
                        speak(f"In front: {labels_str}", priority=1, rate=150)
                    else:
                        speak("No objects detected", priority=1, rate=150)
                except Exception as e:
                    print(f"Quick detection error: {e}")
            
            threading.Thread(target=quick_scan, daemon=True).start()

        # Trigger OCR read on 'r'
        if key == ord('r') or key == ord('R'):
            # Force urgent priority to override background scans
            print("[KEY] 'R' pressed - OCR Read requested")
            # Take a "Snapshot" of the current frame
            snapshot = frame.copy()
            speak("Scanning text", priority=1, rate=160)

            # Extract the ROI to show the user exactly what was "photographed"
            roi_snapshot = snapshot[y_ocr:y_ocr+rh_ocr, x_ocr:x_ocr+rw_ocr]
            cv2.imshow("Captured Picture", roi_snapshot)

            # Fast, low-latency attempt
            text, conf = read_text_from_roi(snapshot, roi=(x_ocr, y_ocr, rw_ocr, rh_ocr), save_debug=False, fast=True)

            if text and conf >= 50:
                speak(f"Text is: {text}", priority=1, rate=150)
                cv2.putText(roi_snapshot, f"Result: {text[:40]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
                cv2.putText(roi_snapshot, f"Conf: {conf:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
                cv2.imshow("Captured Picture", roi_snapshot)
            else:
                # Start background thread to run full ensemble (non-blocking)
                speak("Analyzing", priority=1, rate=150)

                def bg_worker(snap):
                    txt2, conf2 = read_text_from_roi(snap, roi=(x_ocr, y_ocr, rw_ocr, rh_ocr), save_debug=False, fast=False)
                    if txt2:
                        speak(f"Text is: {txt2}", priority=1, rate=150)
                        # update visual (non-blocking)
                        try:
                            rs = snap[y_ocr:y_ocr+rh_ocr, x_ocr:x_ocr+rw_ocr]
                            cv2.putText(rs, f"Result: {txt2[:40]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
                            cv2.putText(rs, f"Conf: {conf2:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
                            cv2.imshow("Captured Picture", rs)
                        except Exception:
                            pass

                threading.Thread(target=bg_worker, args=(snapshot,), daemon=True).start()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys
    print(f"System starting with interpreter: {sys.executable}")
    start_vision_system()
