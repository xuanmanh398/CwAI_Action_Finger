import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, Any

CONFIG_FILE = "settings.json"

@dataclass
class AppConfig:
    # Camera settings
    camera_id: int = 0
    cam_width: int = 640
    cam_height: int = 480
    
    # Active box margins (percentage of frame cropped for tracking to reach screen edges easily)
    frame_margin_x: float = 0.15  # 15% margin left/right
    frame_margin_y: float = 0.15  # 15% margin top/bottom
    
    # Mouse movement settings
    smoothing_factor: float = 0.5  # Exponential Moving Average smoothing (0.1 = smooth/laggy, 0.9 = fast/jittery)
    mouse_speed: float = 1.0
    invert_x: bool = False
    invert_y: bool = False
    
    # Gesture thresholds (distances relative to hand landmark scale)
    pinch_threshold: float = 0.120       # Pinch distance (Normalized distance between Index tip and Thumb tip)
    right_click_threshold: float = 0.120 # Pinch distance between Middle tip and Thumb tip
    double_click_interval: float = 0.35 # Max seconds between 2 pinches for double click
    drag_hold_delay: float = 0.25        # Seconds holding pinch before drag starts
    
    # Scroll settings
    scroll_sensitivity: int = 30         # Pixels scrolled per frame
    scroll_threshold: float = 0.04       # Distance threshold for scroll mode
    
    # Volume control settings
    volume_sensitivity: float = 2.0
    
    # Toggles for features
    enable_mouse_move: bool = True
    enable_left_click: bool = True
    enable_right_click: bool = True
    enable_double_click: bool = True
    enable_drag: bool = True
    enable_scroll: bool = True
    enable_volume: bool = True
    
    # Show Visual Overlay / Camera feed HUD
    show_hud: bool = True
    show_landmarks: bool = True
    show_opencv_window: bool = False

    def save_to_file(self, filepath: str = CONFIG_FILE):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load_from_file(cls, filepath: str = CONFIG_FILE) -> "AppConfig":
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception as e:
                print(f"Error loading config file: {e}. Using defaults.")
        return cls()
