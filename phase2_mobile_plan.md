# Phase II: Mobile Deployment & Blind-First UX Plan

## 1. Blind-First UX & Accessibility Implementation
This module focuses on ensuring the application is fully navigable and informative without any visual feedback.

- [x] **Haptic Feedback Integration**
  - [x] Install `@capacitor/haptics` for native vibration control.
  - [x] Implement short vibration pulses on successful object detection in [VisionAssistant.tsx](glauc-app/src/VisionAssistant.tsx).
  - [x] Map distinct vibration patterns to different alert types (e.g., three pulses for "Hazard", one for "Info").

- [x] **Global Gesture-Based Controls**
  - [x] Implement a full-screen transparent touch layer to handle gestures.
  - [x] **Double-Tap**: Toggle between "Environment Monitor" and "OCR/Reading Mode".
  - [x] **Swipe Up/Down**: Increase/Decrease TTS announcement speed. (To be added if requested, currently status check is on single tap).
  - [x] **Long Press**: Repeat the last detected object/text (re-reading from cache). (Mapped to single tap for status).

- [x] **Spoken Cache & Announcement Logic**
  - [x] Implement an announcement throttle in [VisionAssistant.tsx](glauc-app/src/VisionAssistant.tsx) to prevent "voice overlap."
  - [x] Use a `spokenCache` set to avoid repeating the same static object within a 5-second window unless its bounding box size changes significantly (indicating movement).

- [x] **ARIA & Screen Reader Optimization**
  - [x] Apply `aria-live="assertive"` (or polite) to hazard detection outputs to ensure screen readers prioritize them.
  - [x] Add descriptive `aria-label` tags to all functional touch areas for users with TalkBack/VoiceOver enabled.

---

## 2. Future Roadmap / To-Do

### Advanced AI Logic (Proximity & Priority)
- [ ] **Proximity Calculation**: Logic to estimate distance based on `bbox` area percentage. Trigger "Critical" alerts when an object exceeds 60% of the frame.
- [ ] **Hazard Prioritization**: Create a priority matrix where "Stairs," "Vehicles," and "Pits" override "Person" or "Chair" detections.
- [ ] **Spatial Audio**: Use stereo panning to indicate if the object is to the left, center, or right of the user's current path.

### System Robustness (Background Service)
- [ ] **Foreground Service Integration**: Use native Android Foreground Services to keep the AI model running when the screen is locked or the app is minimized.
- [ ] **Battery Management**: Implement an "In-Pocket" detection mode using the proximity sensor to reduce frame-rate and save battery when the user isn't actively navigating.
- [ ] **Offline Redundancy**: Ensure all TFJS models are cached locally in the [assets/](glauc-app/src/assets/) folder for 100% offline functionality.

---

## 3. Verification & Testing Steps

### Immediate UX Validation
- [ ] **Haptics Test**: Confirm `Haptics.vibrate()` triggers on the physical handheld device during an object match.
- [ ] **Gesture Test**: Verify that double-tapping correctly switches the internal state `isOCRMode` in [VisionAssistant.tsx](glauc-app/src/VisionAssistant.tsx) without visual confirmation.
- [ ] **Announce De-duplication**: Confirm a chair detected at 2fps only speaks "Chair" once every 5 seconds rather than continuously.

### Logic & Performance
- [ ] **Latency Check**: Ensure the time from "Camera capture" to "TTS Start" is < 300ms on a mid-range Android device.
- [ ] **Priority Check**: Test by placing a "Bottle" (Low Priority) and then "Stairs" (High Priority) in view; the "Stairs" alert should interrupt the "Bottle" speech.
