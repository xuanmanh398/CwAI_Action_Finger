from enum import Enum, auto
import math
import time
from typing import Dict, Any, List, Tuple
from config import AppConfig

class GestureType(Enum):
    NONE = auto()
    IDLE_OPEN_PALM = auto()
    PAUSE_FIST = auto()
    POINTING = auto()          # Index extended -> Move Mouse Cursor
    LEFT_PREP = auto()         # Thumb + Index extended -> Freeze Cursor (Prepare Left Click)
    LEFT_PINCH = auto()        # Index bent -> Left Click / Drag
    THUMB_ONLY_PREP = auto()   # Only Thumb extended -> Freeze Cursor (Prepare Right Click)
    RIGHT_PINCH = auto()       # Thumb bent / Thumb+Middle -> Right Click
    SCROLL_MODE = auto()       # Index + Middle extended -> Scroll Up/Down
    VOLUME_MODE = auto()       # Index + Thumb + Pinky extended -> Volume adjust
    PEACE_SIGN = auto()        # Index + Middle V-sign

class GestureState:
    def __init__(self):
        self.current_gesture = GestureType.NONE
        self.cursor_pos: Tuple[float, float] = (0.0, 0.0) # (norm_x, norm_y)
        self.is_pinching_left: bool = False
        self.is_pinching_right: bool = False
        self.pinch_distance_left: float = 0.0
        self.pinch_distance_right: float = 0.0
        self.finger_spread_ratio: float = 0.0
        self.scroll_delta_x: float = 0.0
        self.scroll_delta_y: float = 0.0
        self.continuous_scroll_x: int = 0
        self.continuous_scroll_y: int = 0
        self.volume_level: float = 0.0 # 0.0 to 1.0

class GestureDetector:
    def __init__(self, config: AppConfig):
        self.config = config
        self.prev_scroll_x = None
        self.prev_scroll_y = None
        self.confirmed_gesture = GestureType.NONE
        self.history_gestures: List[GestureType] = []

        # Cursor Freeze Lock to prevent cursor shift during index bend / click
        self.last_pointing_cursor_pos: Tuple[float, float] = (0.5, 0.5)
        self.locked_click_cursor_pos: Tuple[float, float] = None
        self.click_release_time = 0.0

    def finger_states(self, landmarks: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Determines which fingers are extended (True) or folded (False).
        Uses angle-invariant Euclidean geometry relative to wrist.
        """
        if len(landmarks) < 21:
            return {'thumb': False, 'index': False, 'middle': False, 'ring': False, 'pinky': False}

        wrist = landmarks[0]

        def is_finger_extended(tip_idx, pip_idx, mcp_idx):
            tip = landmarks[tip_idx]
            pip = landmarks[pip_idx]
            mcp = landmarks[mcp_idx]
            # Euclidean distance comparison to wrist (angle-invariant)
            dist_tip_wrist = math.hypot(tip['norm_x'] - wrist['norm_x'], tip['norm_y'] - wrist['norm_y'])
            dist_pip_wrist = math.hypot(pip['norm_x'] - wrist['norm_x'], pip['norm_y'] - wrist['norm_y'])
            dist_mcp_wrist = math.hypot(mcp['norm_x'] - wrist['norm_x'], mcp['norm_y'] - wrist['norm_y'])
            return dist_tip_wrist > dist_pip_wrist * 1.05 and dist_pip_wrist > dist_mcp_wrist * 0.9

        index_ext = is_finger_extended(8, 6, 5)
        middle_ext = is_finger_extended(12, 10, 9)
        ring_ext = is_finger_extended(16, 14, 13)
        pinky_ext = is_finger_extended(20, 18, 17)

        # Thumb extension checking relative to pinky MCP landmark 17
        thumb_tip = landmarks[4]
        thumb_mcp = landmarks[2]
        pinky_mcp = landmarks[17]
        dist_thumb_tip = math.hypot(thumb_tip['norm_x'] - pinky_mcp['norm_x'], thumb_tip['norm_y'] - pinky_mcp['norm_y'])
        dist_thumb_mcp = math.hypot(thumb_mcp['norm_x'] - pinky_mcp['norm_x'], thumb_mcp['norm_y'] - pinky_mcp['norm_y'])
        thumb_ext = dist_thumb_tip > dist_thumb_mcp * 1.15

        return {
            'thumb': thumb_ext,
            'index': index_ext,
            'middle': middle_ext,
            'ring': ring_ext,
            'pinky': pinky_ext
        }

    def detect_gesture(self, landmarks: List[Dict[str, Any]], hand_scale: float) -> GestureState:
        state = GestureState()

        if not landmarks or len(landmarks) < 21:
            self.prev_scroll_y = None
            self.history_gestures.clear()
            self.confirmed_gesture = GestureType.NONE
            return state

        fingers = self.finger_states(landmarks)
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]

        index_tip = landmarks[8]
        index_pip = landmarks[6]
        index_mcp = landmarks[5]

        middle_tip = landmarks[12]

        # Calculate scale-invariant and pixel distance pinches
        raw_left_dist = math.hypot(index_tip['norm_x'] - thumb_tip['norm_x'], index_tip['norm_y'] - thumb_tip['norm_y'])
        raw_right_dist = math.hypot(middle_tip['norm_x'] - thumb_tip['norm_x'], middle_tip['norm_y'] - thumb_tip['norm_y'])

        pixel_left_dist = math.hypot(index_tip['cx'] - thumb_tip['cx'], index_tip['cy'] - thumb_tip['cy'])
        pixel_right_dist = math.hypot(middle_tip['cx'] - thumb_tip['cx'], middle_tip['cy'] - thumb_tip['cy'])

        norm_left_pinch = raw_left_dist / hand_scale
        norm_right_pinch = raw_right_dist / hand_scale

        # Index finger bending check
        dist_index_tip_mcp = math.hypot(index_tip['norm_x'] - index_mcp['norm_x'], index_tip['norm_y'] - index_mcp['norm_y'])
        norm_index_bend = dist_index_tip_mcp / hand_scale
        dist_index_tip_wrist = math.hypot(index_tip['norm_x'] - wrist['norm_x'], index_tip['norm_y'] - wrist['norm_y'])
        dist_index_pip_wrist = math.hypot(index_pip['norm_x'] - wrist['norm_x'], index_pip['norm_y'] - wrist['norm_y'])

        # Robust Thumb Extension check (angle & scale invariant)
        dist_thumb_tip_wrist = math.hypot(thumb_tip['norm_x'] - wrist['norm_x'], thumb_tip['norm_y'] - wrist['norm_y'])
        dist_thumb_mcp_wrist = math.hypot(thumb_mcp['norm_x'] - wrist['norm_x'], thumb_mcp['norm_y'] - wrist['norm_y'])
        dist_thumb_index_mcp = math.hypot(thumb_tip['norm_x'] - index_mcp['norm_x'], thumb_tip['norm_y'] - index_mcp['norm_y'])

        norm_thumb_dist_mcp = dist_thumb_index_mcp / hand_scale
        thumb_is_extended = (dist_thumb_tip_wrist > dist_thumb_mcp_wrist * 1.08) or (norm_thumb_dist_mcp > 0.30)

        # Index finger bending & extension check
        dist_index_tip_mcp = math.hypot(index_tip['norm_x'] - index_mcp['norm_x'], index_tip['norm_y'] - index_mcp['norm_y'])
        norm_index_bend = dist_index_tip_mcp / hand_scale
        dist_index_tip_wrist = math.hypot(index_tip['norm_x'] - wrist['norm_x'], index_tip['norm_y'] - wrist['norm_y'])
        dist_index_pip_wrist = math.hypot(index_pip['norm_x'] - wrist['norm_x'], index_pip['norm_y'] - wrist['norm_y'])

        index_is_extended = (norm_index_bend >= 0.38) and (dist_index_tip_wrist > dist_index_pip_wrist * 1.02)
        is_index_bent = (norm_index_bend < 0.38) or (dist_index_tip_wrist <= dist_index_pip_wrist * 0.98)

        # Thumb finger bending check
        dist_thumb_mcp_tip = math.hypot(thumb_tip['norm_x'] - thumb_mcp['norm_x'], thumb_tip['norm_y'] - thumb_mcp['norm_y'])
        norm_thumb_self_bend = dist_thumb_mcp_tip / hand_scale
        is_thumb_bent = (norm_thumb_dist_mcp < 0.28) and (not thumb_is_extended)

        # 3 fingers (Middle, Ring, Pinky) folded into palm
        mrp_folded = not fingers['middle'] and not fingers['ring'] and not fingers['pinky']

        state.is_pinching_left = False
        state.is_pinching_right = False
        is_cursor_frozen = False
        raw_detected_gesture = GestureType.NONE

        num_extended = sum(1 for v in fingers.values() if v)

        # Finger Spread Ratio calculation
        pinky_mcp = landmarks[17]
        pinky_tip = landmarks[20]
        tip_width = math.hypot(index_tip['norm_x'] - pinky_tip['norm_x'], index_tip['norm_y'] - pinky_tip['norm_y'])
        mcp_width = math.hypot(index_mcp['norm_x'] - pinky_mcp['norm_x'], index_mcp['norm_y'] - pinky_mcp['norm_y'])
        spread_ratio = tip_width / max(mcp_width, 0.001)
        state.finger_spread_ratio = spread_ratio
        is_fingers_spread = spread_ratio >= 1.30

        # EVALUATE MUTUALLY EXCLUSIVE POSTURES:

        # 1. HÌNH 2 TRONG YÊU CẦU: THUMB + INDEX EXTENDED (L-Shape / Khóa trỏ chờ Click Trái)
        if thumb_is_extended and (index_is_extended or is_index_bent) and mrp_folded:
            is_cursor_frozen = True
            if is_index_bent or (norm_left_pinch < self.config.pinch_threshold) or (pixel_left_dist < 45):
                state.is_pinching_left = True
                raw_detected_gesture = GestureType.LEFT_PINCH
            else:
                raw_detected_gesture = GestureType.LEFT_PREP

        # 2. HÌNH 1 TRONG YÊU CẦU: ONLY THUMB EXTENDED (Ngón cái giơ mở ra ngoài / Khóa trỏ chờ Click Phải)
        elif thumb_is_extended and (not index_is_extended) and (not is_index_bent) and mrp_folded:
            is_cursor_frozen = True
            if is_thumb_bent or (norm_right_pinch < self.config.right_click_threshold) or (pixel_right_dist < 45):
                state.is_pinching_right = True
                raw_detected_gesture = GestureType.RIGHT_PINCH
            else:
                raw_detected_gesture = GestureType.THUMB_ONLY_PREP

        # 3. TIGHT FIST (Nắm đấm tay thật sự - PAUSE)
        elif (not thumb_is_extended) and (not index_is_extended) and mrp_folded:
            raw_detected_gesture = GestureType.PAUSE_FIST

        # 4. POINTING / MOVING CURSOR (Di chuyển con trỏ chuột mượt mà)
        elif index_is_extended:
            raw_detected_gesture = GestureType.POINTING

        elif is_index_bent and (norm_left_pinch < self.config.pinch_threshold or pixel_left_dist < 45):
            is_cursor_frozen = True
            state.is_pinching_left = True
            raw_detected_gesture = GestureType.LEFT_PINCH

        elif norm_right_pinch < self.config.right_click_threshold or pixel_right_dist < 45:
            is_cursor_frozen = True
            state.is_pinching_right = True
            raw_detected_gesture = GestureType.RIGHT_PINCH

        elif num_extended >= 3 and is_fingers_spread:
            raw_detected_gesture = GestureType.POINTING

        elif num_extended >= 3 and not is_fingers_spread:
            raw_detected_gesture = GestureType.SCROLL_MODE

        elif fingers['index'] and fingers['thumb'] and fingers['pinky'] and not fingers['middle'] and not fingers['ring']:
            raw_detected_gesture = GestureType.VOLUME_MODE

        else:
            raw_detected_gesture = GestureType.POINTING

        # CURSOR POSITION UPDATE LOGIC (CRITICAL FOR MOVEMENT & FREEZE LOCK):
        current_time = time.time()
        if is_cursor_frozen:
            if self.locked_click_cursor_pos is None:
                self.locked_click_cursor_pos = self.last_pointing_cursor_pos
            state.cursor_pos = self.locked_click_cursor_pos
            self.click_release_time = current_time
        else:
            if current_time - self.click_release_time < 0.15 and self.locked_click_cursor_pos is not None:
                state.cursor_pos = self.locked_click_cursor_pos
            else:
                self.locked_click_cursor_pos = None
                self.last_pointing_cursor_pos = (index_tip['norm_x'], index_tip['norm_y'])
                state.cursor_pos = self.last_pointing_cursor_pos

        # Apply Hysteresis Smoothing to gesture transitions
        self.history_gestures.append(raw_detected_gesture)
        if len(self.history_gestures) > 2:
            self.history_gestures.pop(0)

        # Confirm gesture if consistent across buffer or on initial frame
        if self.confirmed_gesture == GestureType.NONE:
            self.confirmed_gesture = raw_detected_gesture
        elif len(self.history_gestures) == 2 and self.history_gestures[0] == self.history_gestures[1]:
            self.confirmed_gesture = self.history_gestures[0]

        state.current_gesture = self.confirmed_gesture

        # Handle continuous 4-direction scroll calculation (Lên/Xuống/Trái/Phải)
        if state.current_gesture == GestureType.SCROLL_MODE:
            hand_center_x = (landmarks[0]['norm_x'] + landmarks[9]['norm_x']) / 2.0
            hand_center_y = (landmarks[0]['norm_y'] + landmarks[9]['norm_y']) / 2.0

            if self.prev_scroll_x is not None and self.prev_scroll_y is not None:
                state.scroll_delta_x = hand_center_x - self.prev_scroll_x
                state.scroll_delta_y = hand_center_y - self.prev_scroll_y

            self.prev_scroll_x = hand_center_x
            self.prev_scroll_y = hand_center_y

            # Calculate continuous directional scroll vector from Wrist (0) to Middle Tip (12)
            wrist_x = landmarks[0]['norm_x']
            wrist_y = landmarks[0]['norm_y']
            dir_x = middle_tip['norm_x'] - wrist_x
            dir_y = middle_tip['norm_y'] - wrist_y

            if dir_y < -0.12:
                state.continuous_scroll_y = -1  # UP
            elif dir_y > 0.12:
                state.continuous_scroll_y = 1   # DOWN

            if dir_x < -0.12:
                state.continuous_scroll_x = -1  # LEFT
            elif dir_x > 0.12:
                state.continuous_scroll_x = 1   # RIGHT
        else:
            self.prev_scroll_x = None
            self.prev_scroll_y = None

        # Handle volume level calculation
        if state.current_gesture == GestureType.VOLUME_MODE:
            vol_range = max(0.01, norm_left_pinch - 0.05)
            state.volume_level = min(1.0, max(0.0, vol_range / 0.30))

        return state
