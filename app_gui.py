import sys
import cv2
import time
import numpy as np

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QCheckBox, QComboBox, QGroupBox,
    QGridLayout, QFrame, QSplitter, QStatusBar, QMessageBox, QDialog
)

from config import AppConfig
from hand_tracker import HandTracker
from gesture_detector import GestureDetector, GestureType
from mouse_controller import MouseController
from hud_overlay import HUDOverlay


class CameraWorker(QThread):
    frame_updated = Signal(QImage, str)
    fps_updated = Signal(int)

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.running = False
        self.cap = None

    def run(self):
        # Open Camera: Try MSMF (Media Foundation) or CAP_ANY first for high FPS on Windows, fallback to CAP_DSHOW
        backends_to_try = [cv2.CAP_MSMF, cv2.CAP_ANY, cv2.CAP_DSHOW]
        self.cap = None

        for backend in backends_to_try:
            try:
                cap = cv2.VideoCapture(self.config.camera_id, backend)
                if cap and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.cam_width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.cam_height)
                    cap.set(cv2.CAP_PROP_FPS, 60)
                    self.cap = cap
                    print(f"[CameraWorker] Opened camera {self.config.camera_id} with backend {backend}")
                    break
            except Exception as e:
                print(f"[CameraWorker] Backend {backend} failed: {e}")

        if not self.cap or not self.cap.isOpened():
            for alt_id in range(3):
                for backend in backends_to_try:
                    try:
                        cap = cv2.VideoCapture(alt_id, backend)
                        if cap and cap.isOpened():
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.cam_width)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.cam_height)
                            cap.set(cv2.CAP_PROP_FPS, 60)
                            self.cap = cap
                            break
                    except Exception:
                        pass
                if self.cap and self.cap.isOpened():
                    break

        if not self.cap or not self.cap.isOpened():
            self.frame_updated.emit(QImage(), "Lỗi: Không tìm thấy Webcam sẵn sàng!")
            return

        tracker = HandTracker(max_hands=1)
        detector = GestureDetector(self.config)
        controller = MouseController(self.config)
        hud = HUDOverlay()

        self.running = True

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Mirror frame horizontally for intuitive interaction
            frame = cv2.flip(frame, 1)

            # Process hand tracking
            annotated_frame, landmarks, hand_obj = tracker.process_frame(frame)
            hand_scale = tracker.get_hand_scale(landmarks)

            # Draw hand connections if enabled
            if self.config.show_landmarks and hand_obj:
                tracker.draw_landmarks(annotated_frame, hand_obj)

            # Detect gesture
            gesture_state = detector.detect_gesture(landmarks, hand_scale)

            # Process mouse & system control action
            controller.process_gesture(gesture_state)

            # Render HUD Overlay on frame with finger labels
            if self.config.show_hud:
                annotated_frame = hud.draw(annotated_frame, gesture_state, self.config, landmarks)

            # Optional OpenCV Window Display
            if self.config.show_opencv_window:
                try:
                    cv2.imshow("Hand Gesture Camera - Cua So Quan Sat", annotated_frame)
                    cv2.waitKey(1)
                except Exception as e:
                    print(f"[CameraWorker Warning] OpenCV HighGUI window failed: {e}")
                    self.config.show_opencv_window = False

            # Convert BGR frame to Qt QImage
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

            self.frame_updated.emit(q_img, gesture_state.current_gesture.name)

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        self.cap.release()

    def stop(self):
        self.running = False
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        self.wait()


class PopoutCameraDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Cửa Sổ Quan Sát Camera Độc Lập")
        self.resize(960, 640)
        self.setMinimumSize(480, 320)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.cam_label = QLabel("Đang tải luồng camera...")
        self.cam_label.setAlignment(Qt.AlignCenter)
        self.cam_label.setStyleSheet("background-color: #11111b; border-radius: 8px;")
        layout.addWidget(self.cam_label, stretch=1)

        btn_layout = QHBoxLayout()
        self.chk_top = QCheckBox("Ghim cửa sổ trên cùng (Always on top)")
        self.chk_top.setChecked(True)
        self.chk_top.toggled.connect(self.toggle_on_top)
        btn_layout.addWidget(self.chk_top)

        btn_layout.addStretch()
        self.btn_fullscreen = QPushButton("📺 Phóng to / Toàn màn hình")
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        btn_layout.addWidget(self.btn_fullscreen)

        layout.addLayout(btn_layout)

    def toggle_on_top(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def update_frame(self, q_img):
        if not q_img.isNull():
            pixmap = QPixmap.fromImage(q_img).scaled(
                self.cam_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.cam_label.setPixmap(pixmap)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = AppConfig.load_from_file()
        self.worker = None
        self.popout_dialog = None

        self.setWindowTitle("Hand Gesture Controller - Điều khiển Máy tính bằng Camera")
        self.resize(1280, 760)
        self.setMinimumSize(1000, 650)

        self.apply_dark_theme()
        self.init_ui()
        # Auto-start camera tracking when application opens
        QTimer.singleShot(400, self.start_tracking)

    def apply_dark_theme(self):
        qss = """
        QMainWindow {
            background-color: #1e1e2e;
            color: #cdd6f4;
        }
        QWidget {
            background-color: #1e1e2e;
            color: #cdd6f4;
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #45475a;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 10px;
            background-color: #181825;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 5px;
            color: #89b4fa;
        }
        QPushButton {
            background-color: #313244;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45475a;
            border-color: #89b4fa;
        }
        QPushButton:pressed {
            background-color: #585b70;
        }
        QPushButton#start_btn {
            background-color: #a6e3a1;
            color: #11111b;
            font-size: 14px;
        }
        QPushButton#start_btn:hover {
            background-color: #94e2d5;
        }
        QPushButton#stop_btn {
            background-color: #f38ba8;
            color: #11111b;
            font-size: 14px;
        }
        QPushButton#stop_btn:hover {
            background-color: #eba0ac;
        }
        QSlider::groove:horizontal {
            height: 6px;
            background: #313244;
            border-radius: 3px;
        }
        QSlider::sub-page:horizontal {
            background: #89b4fa;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #b4befe;
            width: 16px;
            margin-top: -5px;
            margin-bottom: -5px;
            border-radius: 8px;
        }
        QCheckBox {
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #45475a;
            background-color: #313244;
        }
        QCheckBox::indicator:checked {
            background-color: #89b4fa;
            border-color: #89b4fa;
        }
        QComboBox {
            background-color: #313244;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 5px 10px;
        }
        QLabel#status_badge {
            background-color: #313244;
            border: 1px solid #89b4fa;
            border-radius: 6px;
            padding: 6px;
            font-weight: bold;
            color: #a6e3a1;
        }
        """
        self.setStyleSheet(qss)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ---------------- LEFT PANEL: Video Display ----------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Title / Status Header
        header_layout = QHBoxLayout()
        title_label = QLabel("📷 Luồng Camera Tracking")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()
        self.status_badge = QLabel("Trạng thái: Tắt", objectName="status_badge")
        header_layout.addWidget(self.status_badge)

        left_layout.addLayout(header_layout)

        # Video Frame Container
        self.video_label = QLabel("Nhấn 'Bắt đầu Control' để mở Camera")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #11111b; border-radius: 10px; border: 1px solid #313244;")
        self.video_label.setMinimumSize(640, 480)
        left_layout.addWidget(self.video_label, stretch=1)

        # Camera Control Bar
        cam_bar = QHBoxLayout()
        cam_bar.addWidget(QLabel("Chọn Camera:"))
        self.cam_combo = QComboBox()
        self.detect_cameras()
        cam_bar.addWidget(self.cam_combo)

        self.btn_start = QPushButton("▶ Bắt đầu Control", objectName="start_btn")
        self.btn_start.clicked.connect(self.start_tracking)
        cam_bar.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Tạm dừng", objectName="stop_btn")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_tracking)
        cam_bar.addWidget(self.btn_stop)

        self.btn_popout = QPushButton("🔍 Cửa sổ Camera Độc Lập")
        self.btn_popout.clicked.connect(self.open_popout_camera)
        cam_bar.addWidget(self.btn_popout)

        left_layout.addLayout(cam_bar)

        # ---------------- RIGHT PANEL: Settings & Guide ----------------
        right_panel = QWidget()
        right_panel.setFixedWidth(360)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Tuning Controls Box
        tuning_group = QGroupBox("⚙️ Cấu hình Độ nhạy & Chuột")
        tuning_layout = FormGridLayout()

        # Smoothing Slider
        self.smooth_label = QLabel(f"{int(self.config.smoothing_factor * 100)}%")
        self.smooth_slider = QSlider(Qt.Horizontal)
        self.smooth_slider.setRange(10, 90)
        self.smooth_slider.setValue(int(self.config.smoothing_factor * 100))
        self.smooth_slider.valueChanged.connect(self.on_smooth_changed)
        tuning_layout.addRow("Độ mượt chuột (Smooth):", self.smooth_slider, self.smooth_label)

        # Margin Crop Slider
        self.margin_label = QLabel(f"{int(self.config.frame_margin_x * 100)}%")
        self.margin_slider = QSlider(Qt.Horizontal)
        self.margin_slider.setRange(5, 30)
        self.margin_slider.setValue(int(self.config.frame_margin_x * 100))
        self.margin_slider.valueChanged.connect(self.on_margin_changed)
        tuning_layout.addRow("Vùng phủ màn hình (Margin):", self.margin_slider, self.margin_label)

        # Pinch Threshold Slider
        self.pinch_label = QLabel(f"{int(self.config.pinch_threshold * 1000)}")
        self.pinch_slider = QSlider(Qt.Horizontal)
        self.pinch_slider.setRange(20, 80)
        self.pinch_slider.setValue(int(self.config.pinch_threshold * 1000))
        self.pinch_slider.valueChanged.connect(self.on_pinch_changed)
        tuning_layout.addRow("Độ nhạy Bóp ngón (Pinch):", self.pinch_slider, self.pinch_label)

        tuning_group.setLayout(tuning_layout)
        right_layout.addWidget(tuning_group)

        # 2. Features Toggle Box
        features_group = QGroupBox("🎯 Bật/Tắt Tính năng")
        features_layout = QGridLayout()

        self.chk_move = QCheckBox("Di chuyển con trỏ")
        self.chk_move.setChecked(self.config.enable_mouse_move)
        self.chk_move.toggled.connect(lambda v: setattr(self.config, 'enable_mouse_move', v))
        features_layout.addWidget(self.chk_move, 0, 0)

        self.chk_click = QCheckBox("Click chuột trái")
        self.chk_click.setChecked(self.config.enable_left_click)
        self.chk_click.toggled.connect(lambda v: setattr(self.config, 'enable_left_click', v))
        features_layout.addWidget(self.chk_click, 0, 1)

        self.chk_rclick = QCheckBox("Click chuột phải")
        self.chk_rclick.setChecked(self.config.enable_right_click)
        self.chk_rclick.toggled.connect(lambda v: setattr(self.config, 'enable_right_click', v))
        features_layout.addWidget(self.chk_rclick, 1, 0)

        self.chk_drag = QCheckBox("Kéo và thả (Drag)")
        self.chk_drag.setChecked(self.config.enable_drag)
        self.chk_drag.toggled.connect(lambda v: setattr(self.config, 'enable_drag', v))
        features_layout.addWidget(self.chk_drag, 1, 1)

        self.chk_scroll = QCheckBox("Cuộn trang (Scroll)")
        self.chk_scroll.setChecked(self.config.enable_scroll)
        self.chk_scroll.toggled.connect(lambda v: setattr(self.config, 'enable_scroll', v))
        features_layout.addWidget(self.chk_scroll, 2, 0)

        self.chk_vol = QCheckBox("Âm lượng hệ thống")
        self.chk_vol.setChecked(self.config.enable_volume)
        self.chk_vol.toggled.connect(lambda v: setattr(self.config, 'enable_volume', v))
        features_layout.addWidget(self.chk_vol, 2, 1)

        self.chk_hud = QCheckBox("Hiển thị HUD Overlay")
        self.chk_hud.setChecked(self.config.show_hud)
        self.chk_hud.toggled.connect(lambda v: setattr(self.config, 'show_hud', v))
        features_layout.addWidget(self.chk_hud, 3, 0)

        self.chk_lm = QCheckBox("Vẽ Xương bàn tay")
        self.chk_lm.setChecked(self.config.show_landmarks)
        self.chk_lm.toggled.connect(lambda v: setattr(self.config, 'show_landmarks', v))
        features_layout.addWidget(self.chk_lm, 3, 1)

        self.chk_opencv = QCheckBox("Cửa sổ xem OpenCV")
        self.chk_opencv.setChecked(self.config.show_opencv_window)
        self.chk_opencv.toggled.connect(lambda v: setattr(self.config, 'show_opencv_window', v))
        features_layout.addWidget(self.chk_opencv, 4, 0)

        self.chk_inv_x = QCheckBox("Đảo chiều X (Trái/Phải)")
        self.chk_inv_x.setChecked(self.config.invert_x)
        self.chk_inv_x.toggled.connect(lambda v: setattr(self.config, 'invert_x', v))
        features_layout.addWidget(self.chk_inv_x, 4, 1)

        self.chk_inv_y = QCheckBox("Đảo chiều Y (Lên/Xuống)")
        self.chk_inv_y.setChecked(self.config.invert_y)
        self.chk_inv_y.toggled.connect(lambda v: setattr(self.config, 'invert_y', v))
        features_layout.addWidget(self.chk_inv_y, 5, 0)

        features_group.setLayout(features_layout)
        right_layout.addWidget(features_group)

        # 3. Gesture Guide Box
        guide_group = QGroupBox("📖 Hướng dẫn Cử chỉ Tay")
        guide_layout = QVBoxLayout()
        
        guide_text = (
            "<b>✋ Xòe bàn tay rộng ngón:</b> Di chuyển con trỏ chuột<br>"
            "<b>🖐️ Khép các ngón tay cạnh nhau:</b> Vuốt 4 Hướng (Lên / Xuống / Trái / Phải)<br>"
            "<b>👇 Gập ngón trỏ xuống:</b> Click chuột trái (Tap Index Click)<br>"
            "<b>👌 Bóp Ngón cái + Ngón trỏ:</b> Left Click (Giữ >0.3s để Drag)<br>"
            "<b>🤏 Bóp Ngón cái + Ngón giữa:</b> Right Click chuột phải<br>"
            "<b>🤟 Ngón cái + Ngón trỏ + Út:</b> Tăng / Giảm âm lượng<br>"
            "<b>✊ Nắm tay (Fist):</b> Tạm dừng Tracking chuột"
        )
        guide_label = QLabel(guide_text)
        guide_label.setWordWrap(True)
        guide_label.setStyleSheet("line-height: 1.4; color: #a6adc8; padding: 4px;")
        guide_layout.addWidget(guide_label)
        guide_group.setLayout(guide_layout)
        right_layout.addWidget(guide_group)

        # Save settings button
        btn_save = QPushButton("💾 Lưu Cấu Hình Default")
        btn_save.clicked.connect(self.save_config)
        right_layout.addWidget(btn_save)

        right_layout.addStretch()

        # Assembly Layout
        main_layout.addWidget(left_panel, stretch=3)
        main_layout.addWidget(right_panel, stretch=1)

        # Status Bar
        self.statusBar().showMessage("Sẵn sàng")

    def detect_cameras(self):
        self.cam_combo.clear()
        for i in range(3):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                self.cam_combo.addItem(f"Camera {i}", i)
                cap.release()
        if self.cam_combo.count() == 0:
            self.cam_combo.addItem("Camera 0", 0)

    def start_tracking(self):
        self.config.camera_id = self.cam_combo.currentData()
        self.worker = CameraWorker(self.config)
        self.worker.frame_updated.connect(self.update_frame)
        self.worker.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.cam_combo.setEnabled(False)
        self.status_badge.setText("Trạng thái: Đang chạy 🟢")
        self.status_badge.setStyleSheet("border: 1px solid #a6e3a1; color: #a6e3a1;")

    def stop_tracking(self):
        if self.worker:
            self.worker.stop()
            self.worker = None

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.cam_combo.setEnabled(True)
        self.video_label.setText("Đã dừng Tracking camera")
        self.status_badge.setText("Trạng thái: Đã dừng 🔴")
        self.status_badge.setStyleSheet("border: 1px solid #f38ba8; color: #f38ba8;")

    def open_popout_camera(self):
        if not self.popout_dialog:
            self.popout_dialog = PopoutCameraDialog(self)
        self.popout_dialog.show()
        self.popout_dialog.raise_()
        self.popout_dialog.activateWindow()

    @Slot(QImage, str)
    def update_frame(self, q_img, gesture_name):
        if not q_img.isNull():
            scaled_pixmap = QPixmap.fromImage(q_img).scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)
            self.statusBar().showMessage(f"Đang nhận diện cử chỉ: {gesture_name}")

            if self.popout_dialog and self.popout_dialog.isVisible():
                self.popout_dialog.update_frame(q_img)

    def on_smooth_changed(self, val):
        self.config.smoothing_factor = val / 100.0
        self.smooth_label.setText(f"{val}%")

    def on_margin_changed(self, val):
        self.config.frame_margin_x = val / 100.0
        self.config.frame_margin_y = val / 100.0
        self.margin_label.setText(f"{val}%")

    def on_pinch_changed(self, val):
        self.config.pinch_threshold = val / 1000.0
        self.config.right_click_threshold = val / 1000.0
        self.pinch_label.setText(f"{val}")

    def save_config(self):
        self.config.save_to_file()
        QMessageBox.information(self, "Lưu cấu hình", "Cấu hình đã được lưu thành công vào settings.json!")

    def closeEvent(self, event):
        self.stop_tracking()
        event.accept()


class FormGridLayout(QGridLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalSpacing(10)
        self.setHorizontalSpacing(10)
        self._current_row = 0

    def addRow(self, label_text, widget, val_label=None):
        lbl = QLabel(label_text)
        self.addWidget(lbl, self._current_row, 0)
        self.addWidget(widget, self._current_row, 1)
        if val_label is not None:
            self.addWidget(val_label, self._current_row, 2)
        self._current_row += 1


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
