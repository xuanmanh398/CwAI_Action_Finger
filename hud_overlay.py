import cv2
import numpy as np
import time
from gesture_detector import GestureState, GestureType
from config import AppConfig

class HUDOverlay:
    def __init__(self):
        self.prev_time = time.time()
        self.fps = 0.0

    def calculate_fps(self):
        curr_time = time.time()
        dt = curr_time - self.prev_time
        self.prev_time = curr_time
        if dt > 0:
            self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)
        return int(self.fps)

    def draw(self, img, gesture_state: GestureState, config: AppConfig, landmarks=None):
        h, w, c = img.shape
        fps = self.calculate_fps()

        # 1. Draw Active Control Region Box
        margin_x = int(w * config.frame_margin_x)
        margin_y = int(h * config.frame_margin_y)
        
        # Semi-transparent overlay box for active region
        overlay = img.copy()
        cv2.rectangle(overlay, (margin_x, margin_y), (w - margin_x, h - margin_y), (0, 255, 255), 2)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
        
        cv2.putText(img, "Vung Dieu Khien (Active Area)", (margin_x + 5, margin_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        # 2. Draw FPS Badge
        cv2.rectangle(img, (10, 10), (120, 45), (30, 30, 30), -1)
        cv2.rectangle(img, (10, 10), (120, 45), (100, 100, 100), 1)
        cv2.putText(img, f"FPS: {fps}", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

        gesture_name_vi = {
            GestureType.POINTING: "XOE BAN TAY (Di chuyen con tro)",
            GestureType.LEFT_PREP: "[KHOA TRO] CHO CLICK TRAI (Gap ngon tro)",
            GestureType.LEFT_PINCH: "[CLICK TRAI] GAP NGON TRO (Dung tro)",
            GestureType.THUMB_ONLY_PREP: "[KHOA TRO] CHO CLICK PHAI (Gap ngon cai)",
            GestureType.RIGHT_PINCH: "[CLICK PHAI] GAP NGON CAI (Dung tro)",
            GestureType.SCROLL_MODE: "KHEP NGON TAY (Vuot 4 Huong)",
            GestureType.VOLUME_MODE: "[VOLUME] CHINH AM LUONG",
            GestureType.PAUSE_FIST: "[PAUSE] NAM TAY",
            GestureType.IDLE_OPEN_PALM: "[IDLE] XOE TAY",
            GestureType.NONE: "Tim ban tay..."
        }
        text_display = gesture_name_vi.get(gesture_state.current_gesture, gesture_state.current_gesture.name)
        
        color_map = {
            GestureType.POINTING: (0, 255, 0),          # Green
            GestureType.LEFT_PREP: (0, 255, 255),        # Cyan
            GestureType.LEFT_PINCH: (255, 0, 0),        # Blue
            GestureType.THUMB_ONLY_PREP: (0, 255, 255),   # Cyan
            GestureType.RIGHT_PINCH: (255, 165, 0),     # Orange
            GestureType.SCROLL_MODE: (255, 0, 255),     # Magenta
            GestureType.VOLUME_MODE: (0, 255, 255),     # Yellow
            GestureType.PAUSE_FIST: (0, 0, 255),        # Red
            GestureType.IDLE_OPEN_PALM: (200, 200, 200),
            GestureType.NONE: (100, 100, 100)
        }
        badge_color = color_map.get(gesture_state.current_gesture, (255, 255, 255))

        # Status Bar at top right
        cv2.rectangle(img, (w - 360, 10), (w - 10, 45), (30, 30, 30), -1)
        cv2.rectangle(img, (w - 360, 10), (w - 10, 45), badge_color, 2)
        cv2.putText(img, text_display, (w - 350, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, badge_color, 2, cv2.LINE_AA)

        # Pinch Distance & Finger Spread Info Badge
        pinch_info = f"Pinch: {gesture_state.pinch_distance_left:.3f} | Spread Ratio: {gesture_state.finger_spread_ratio:.2f}"
        cv2.putText(img, pinch_info, (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        # 4. Highlight & Label Recognized Finger Tips
        if landmarks and len(landmarks) >= 21:
            finger_tips = [
                (4, "Ngon cai (Thumb)", (0, 165, 255)),
                (8, "Ngon tro (Cursor)", (0, 255, 0)),
                (12, "Ngon giua (Middle)", (255, 0, 255)),
                (16, "Ap ut (Ring)", (255, 255, 0)),
                (20, "Ngon ut (Pinky)", (255, 0, 0))
            ]

            for lm_idx, label, color in finger_tips:
                lm = landmarks[lm_idx]
                cx, cy = lm['cx'], lm['cy']
                cv2.circle(img, (cx, cy), 7, color, -1)
                cv2.circle(img, (cx, cy), 11, (255, 255, 255), 1)
                cv2.putText(img, label, (cx + 12, cy + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        # 5. Draw Cursor Target Indicator on Frame
        if gesture_state.cursor_pos != (0.0, 0.0):
            cx = int(gesture_state.cursor_pos[0] * w)
            cy = int(gesture_state.cursor_pos[1] * h)
            
            dot_color = (0, 255, 0) if not gesture_state.is_pinching_left else (0, 0, 255)
            cv2.circle(img, (cx, cy), 9, dot_color, -1)
            cv2.circle(img, (cx, cy), 16, (255, 255, 255), 2)

        return img
