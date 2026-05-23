# IWY Glaucoma Assistant: Master Future Roadmap

This document outlines the long-term vision and technical evolution for the IWY Assistant, specifically focusing on advanced accessibility and personalized safety.

## Phase III: Personalized AI for Home Safety (Concept)

The primary objective of Phase III is to transition from a generic detection model to a **Personalized Safety Assistant** that understands the unique geometry of a patient's home.

### 1. Personalized Object Recognition
Instead of relying solely on the 80 generic COCO-SSD labels, the app will allow users to "train" the AI on their specific indoor environment.
- **Custom Classes**: "Kitchen Step," "Glass Coffee Table," "Low-hanging Cabinet," "Favorite Armchair."
- **Home Mapping**: A guided "Setup Mode" where a caretaker scans rooms to identify and label static hazards.

### 2. Technical Implementation
- **Transfer Learning**: Utilizing a pre-trained backbone (like YOLOv8 or MobileNetV3) and performing fine-tuning on a small, user-provided dataset (50-100 images per hazard).
- **Edge Training**: If hardware permits, training can occur on-device; otherwise, a secure local server or private cloud instance will process the custom model weights.
- **Depth Integration**: leveraging LiDAR (on high-end devices) to provide centimeter-level accuracy for the custom home-map.

### 3. Impact on Glaucoma Safety
- **Solving the "Stairs" Problem**: Generic AI often misses specific types of domestic stairs. Personalized training ensures 100% reliability for the stairs the patient uses daily.
- **Low Contrast Detection**: Training on the patient's actual furniture allows the AI to recognize obstacles even in sub-optimal lighting or low-contrast scenarios (e.g., a white chair against a white wall).
- **Predictive Guidance**: By knowing the layout of the home, the AI can alert the user *approaching* a hazard before they are even in its line of sight.

## Phase IV: Ecosystem & Wearable Integration
- **Haptic Vest/Belt**: Moving feedback from the phone to a spatial haptic wearable for true "Hands-Free" navigation.
- **Smart Glass Support**: Porting the IWY logic to AR glasses (like Ray-Ban Meta or Apple Vision Pro) to provide constant, head-mounted environment scanning.
