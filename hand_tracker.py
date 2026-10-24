import os
import cv2
import math
import time
import numpy as np
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

# Standard 21 Hand Landmark Connections
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # Index
    (5, 9), (9, 10), (10, 11), (11, 12),      # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),    # Ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Pinky & Palm
]

class HandTracker:
    def __init__(self, mode=False, max_hands=1, detection_con=0.45, track_con=0.45):
        self.max_hands = max_hands
        self.ensure_model_downloaded()

        # Landmark persistence memory to smooth out single-frame motion blur drops
        self.last_landmarks_list = []
        self.last_hand_landmarks_obj = None
        self.missed_frame_count = 0
        self.max_missed_persistence = 3

        try:
            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_hands=self.max_hands,
                min_hand_detection_confidence=detection_con,
                min_hand_presence_confidence=track_con
            )
            self.landmarker = vision.HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"[HandTracker Error] Failed to initialize HandLandmarker: {e}")
            self.landmarker = None

    def ensure_model_downloaded(self):
        if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 1000:
            print(f"[HandTracker] Downloading model file to {MODEL_PATH}...")
            try:
                urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
                print("[HandTracker] Model downloaded successfully!")
            except Exception as e:
                print(f"[HandTracker Error] Failed to download model: {e}")

    def process_frame(self, img):
        landmarks_list = []
        hand_landmarks_obj = None

        if not self.landmarker:
            return img, landmarks_list, hand_landmarks_obj

        h, w, c = img.shape
        rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Downscale frame for fast MediaPipe inference (MediaPipe internal tensor size is 224x224)
        proc_w = 320
        proc_h = int(h * (proc_w / w))
        small_rgb = cv2.resize(rgb_frame, (proc_w, proc_h), interpolation=cv2.INTER_NEAREST)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=small_rgb)

        # Use VIDEO mode with timestamp for optical-flow temporal tracking
        timestamp_ms = int(time.time() * 1000)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        if result and result.hand_landmarks and len(result.hand_landmarks) > 0:
            primary_hand = result.hand_landmarks[0]
            hand_landmarks_obj = primary_hand

            for idx, lm in enumerate(primary_hand):
                cx, cy = int(lm.x * w), int(lm.y * h)
                landmarks_list.append({
                    'id': idx,
                    'cx': cx,
                    'cy': cy,
                    'norm_x': lm.x,
                    'norm_y': lm.y,
                    'z': lm.z
                })

            # Save to persistence buffer
            self.last_landmarks_list = landmarks_list
            self.last_hand_landmarks_obj = hand_landmarks_obj
            self.missed_frame_count = 0
        else:
            # Handle brief motion blur drops with short memory buffer
            self.missed_frame_count += 1
            if self.missed_frame_count <= self.max_missed_persistence and self.last_landmarks_list:
                landmarks_list = self.last_landmarks_list
                hand_landmarks_obj = self.last_hand_landmarks_obj

        return img, landmarks_list, hand_landmarks_obj

    def draw_landmarks(self, img, hand_landmarks_obj):
        """
        Draws hand joint connections and landmarks on the OpenCV frame.
        """
        if not hand_landmarks_obj:
            return

        h, w, c = img.shape
        coords = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks_obj]

        # Draw bones
        for start_idx, end_idx in HAND_CONNECTIONS:
            if start_idx < len(coords) and end_idx < len(coords):
                p1 = coords[start_idx]
                p2 = coords[end_idx]
                cv2.line(img, p1, p2, (245, 117, 66), 2, cv2.LINE_AA)

        # Draw joints
        for idx, (cx, cy) in enumerate(coords):
            # Highlight tips with larger circles
            if idx in (4, 8, 12, 16, 20):
                cv2.circle(img, (cx, cy), 6, (0, 255, 0), -1)
                cv2.circle(img, (cx, cy), 8, (255, 255, 255), 1)
            else:
                cv2.circle(img, (cx, cy), 4, (255, 255, 255), -1)

    @staticmethod
    def calculate_distance(p1, p2):
        dx = p1['norm_x'] - p2['norm_x']
        dy = p1['norm_y'] - p2['norm_y']
        return math.hypot(dx, dy)

    @staticmethod
    def get_hand_scale(landmarks):
        if landmarks and len(landmarks) >= 21:
            wrist = landmarks[0]
            middle_mcp = landmarks[9]
            index_mcp = landmarks[5]
            pinky_mcp = landmarks[17]

            # Length scale (Wrist to Middle MCP)
            dist_length = math.hypot(wrist['norm_x'] - middle_mcp['norm_x'], wrist['norm_y'] - middle_mcp['norm_y'])
            # Width scale (Index MCP to Pinky MCP across palm)
            dist_width = math.hypot(index_mcp['norm_x'] - pinky_mcp['norm_x'], index_mcp['norm_y'] - pinky_mcp['norm_y'])

            # Max scale avoids scale distortion when hand is angled towards camera
            return max(dist_length, dist_width, 0.05)
        return 1.0
