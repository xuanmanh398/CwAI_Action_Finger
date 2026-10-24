import time
import pyautogui
from config import AppConfig
from gesture_detector import GestureState, GestureType

# Ensure PyAutoGUI is responsive and doesn't throw FailSafeException on screen edges
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.001

class MouseController:
    def __init__(self, config: AppConfig):
        self.config = config
        self.screen_width, self.screen_height = pyautogui.size()

        # Target and smoothed cursor position
        self.smoothed_x = self.screen_width / 2.0
        self.smoothed_y = self.screen_height / 2.0

        # Click state variables
        self.is_dragging = False
        self.left_pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.was_pinching_left = False
        self.was_pinching_right = False
        
        # Volume & Scroll throttle
        self.last_vol_change_time = 0.0
        self.last_scroll_time = 0.0

    def update_screen_size(self):
        self.screen_width, self.screen_height = pyautogui.size()

    def map_coords(self, norm_x: float, norm_y: float) -> tuple[float, float]:
        """
        Maps normalized camera coordinates (0.0..1.0) to screen pixel coordinates,
        taking into account active margin cropping and camera mirroring.
        """
        margin_x = self.config.frame_margin_x
        margin_y = self.config.frame_margin_y

        # Clamp normalized coords within margins
        clamped_x = max(margin_x, min(1.0 - margin_x, norm_x))
        clamped_y = max(margin_y, min(1.0 - margin_y, norm_y))

        # Re-scale to 0.0 .. 1.0 within the active margin box
        rel_x = (clamped_x - margin_x) / (1.0 - 2 * margin_x)
        rel_y = (clamped_y - margin_y) / (1.0 - 2 * margin_y)

        # Mirroring: Camera image is already flipped horizontally in CameraWorker
        if self.config.invert_x:
            rel_x = 1.0 - rel_x
        if self.config.invert_y:
            rel_y = 1.0 - rel_y

        target_x = rel_x * self.screen_width
        target_y = rel_y * self.screen_height
        return target_x, target_y

    def smooth_movement(self, target_x: float, target_y: float) -> tuple[int, int]:
        """
        Applies Exponential Moving Average (EMA) smoothing filter to mouse movement.
        """
        alpha = self.config.smoothing_factor
        self.smoothed_x = self.smoothed_x + alpha * (target_x - self.smoothed_x)
        self.smoothed_y = self.smoothed_y + alpha * (target_y - self.smoothed_y)
        return int(self.smoothed_x), int(self.smoothed_y)

    def process_gesture(self, state: GestureState):
        current_time = time.time()

        # 1. Cursor Movement & Dragging
        if self.config.enable_mouse_move and state.cursor_pos != (0.0, 0.0):
            target_x, target_y = self.map_coords(state.cursor_pos[0], state.cursor_pos[1])
            final_x, final_y = self.smooth_movement(target_x, target_y)

            # Move mouse during POINTING / default tracking mode or when DRAGGING.
            # Freeze mouse movement during frozen prep postures (LEFT_PREP, THUMB_ONLY_PREP, PAUSE_FIST, or active clicks)
            frozen_gestures = (GestureType.LEFT_PREP, GestureType.LEFT_PINCH, GestureType.THUMB_ONLY_PREP, GestureType.RIGHT_PINCH, GestureType.PAUSE_FIST)
            if (state.current_gesture not in frozen_gestures and not state.is_pinching_left and not state.is_pinching_right) or self.is_dragging:
                pyautogui.moveTo(final_x, final_y)

        # 2. Left Click / Drag Logic
        if self.config.enable_left_click or self.config.enable_drag:
            # Left Pinch Started
            if state.is_pinching_left and not self.was_pinching_left:
                self.left_pinch_start_time = current_time

            # Left Pinch Held -> Dragging
            elif state.is_pinching_left and self.was_pinching_left:
                duration = current_time - self.left_pinch_start_time
                if duration >= self.config.drag_hold_delay and not self.is_dragging and self.config.enable_drag:
                    pyautogui.mouseDown(button='left')
                    self.is_dragging = True

            # Left Pinch Released
            elif not state.is_pinching_left and self.was_pinching_left:
                duration = current_time - self.left_pinch_start_time
                if self.is_dragging:
                    pyautogui.mouseUp(button='left')
                    self.is_dragging = False
                elif duration < self.config.drag_hold_delay:
                    # Quick tap -> Click or Double Click
                    if (current_time - self.last_click_time) < self.config.double_click_interval and self.config.enable_double_click:
                        pyautogui.doubleClick(button='left')
                        self.last_click_time = 0.0
                    else:
                        pyautogui.click(button='left')
                        self.last_click_time = current_time

            self.was_pinching_left = state.is_pinching_left

        # 3. Right Click Logic
        if self.config.enable_right_click:
            if not state.is_pinching_right and self.was_pinching_right:
                pyautogui.click(button='right')
            self.was_pinching_right = state.is_pinching_right

        # 4. 4-Direction Scroll & Swipe Logic (Lên / Xuống / Trái / Phải)
        if self.config.enable_scroll and state.current_gesture == GestureType.SCROLL_MODE:
            # 1. Delta Movement Scroll (Vuốt di chuyển tay)
            if abs(state.scroll_delta_y) > 0.003:
                clicks_y = int(-state.scroll_delta_y * self.config.scroll_sensitivity * 120)
                if clicks_y != 0:
                    pyautogui.scroll(clicks_y)

            if abs(state.scroll_delta_x) > 0.005:
                clicks_x = int(state.scroll_delta_x * self.config.scroll_sensitivity * 120)
                if self.config.invert_x:
                    clicks_x = -clicks_x
                if clicks_x != 0:
                    try:
                        pyautogui.hscroll(clicks_x)
                    except Exception:
                        pass

            # 2. Continuous Scroll while holding hand in directional pose (Giữ nguyên tay)
            if current_time - self.last_scroll_time > 0.04:  # ~25 scrolls per second
                if state.continuous_scroll_y != 0:
                    amount_y = int(-state.continuous_scroll_y * self.config.scroll_sensitivity * 4)
                    pyautogui.scroll(amount_y)
                    self.last_scroll_time = current_time

                if state.continuous_scroll_x != 0:
                    amount_x = int(state.continuous_scroll_x * self.config.scroll_sensitivity * 4)
                    if self.config.invert_x:
                        amount_x = -amount_x
                    try:
                        pyautogui.hscroll(amount_x)
                    except Exception:
                        pass
                    self.last_scroll_time = current_time

        # 5. Volume Logic
        if self.config.enable_volume and state.current_gesture == GestureType.VOLUME_MODE:
            if current_time - self.last_vol_change_time > 0.15:
                # Scale volume level (0.0 to 1.0)
                if state.volume_level > 0.6:
                    pyautogui.press('volumeup')
                    self.last_vol_change_time = current_time
                elif state.volume_level < 0.3:
                    pyautogui.press('volumedown')
                    self.last_vol_change_time = current_time
