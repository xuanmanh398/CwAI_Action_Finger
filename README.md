# Hand Gesture Computer Controller - Phần Mềm Điều Khiển Máy Tính Bằng Camera & Cử Chỉ Tay

Phần mềm điều khiển máy tính không cần chuột/bàn phím thông qua Webcam, sử dụng thị giác máy tính với **OpenCV**, **MediaPipe Hand Tracking (Tasks API)** và giao diện **PySide6 (Qt6)**.

---

## 🌟 Tính Năng Nổi Bật

- **Di chuyển con trỏ chuột mượt mà (Smooth Cursor Navigation):**
  - Thuật toán lọc **Exponential Moving Average (EMA)** triệt tiêu hiện tượng rung tay (jittering).
  - Tự động căn viền màn hình (Active Control Margin Box) giúp dễ dàng di chuyển chuột tới 4 góc màn hình.

- **Thao tác chuột linh hoạt (Single-Finger & Pinch Click):**
  - **Click chuột trái (Left Click):** Chỉ cần **Gập nhẹ ngón trỏ xuống (Tap Index Finger)** HOẶC Bóp ngón cái & ngón trỏ (Pinch Index).
  - **Double Click:** Gập nhấp ngón trỏ 2 lần nhanh.
  - **Kéo và thả (Click & Drag):** Gập giữ ngón trỏ trên 0.3s hoặc giữ bóp ngón trỏ và di chuyển.
  - **Click chuột phải (Right Click):** Bóp ngón cái & ngón giữa (Pinch Middle).
  - **Cuộn trang (Scroll Up / Down):** Giơ 2 ngón (Ngón trỏ + Ngón giữa) và di chuyển tay lên / xuống.

- **Điều khiển Hệ thống (System Control):**
  - **Âm lượng (Volume Control):** Cử chỉ 3 ngón (Cái + Trỏ + Út - Rock Sign 🤟) tăng/giảm âm lượng.
  - **Tạm dừng (Pause Tracking):** Nắm tay lại (Fist ✊) để tạm dừng di chuyển chuột an toàn.

---

## 🖐️ Bảng Hướng Dẫn Cử Chỉ Tay (Gesture Shortcuts)

| Cử chỉ (Gesture) | Thao tác trên máy tính |
|---|---|
| ☝️ **Chỉ ngón trỏ thẳng** | Di chuyển con trỏ chuột |
| 👇 **Gập ngón trỏ xuống (Tap Index)** | Click chuột trái (Single Finger Click) |
| 👌 **Bóp Ngón cái + Ngón trỏ** | Click chuột trái (Giữ > 0.3s để Kéo/Thả) |
| 🤏 **Bóp Ngón cái + Ngón giữa** | Click chuột phải (Right Click) |
| ✌️ **Ngón trỏ + Ngón giữa** | Cuộn trang (Di chuyển tay Lên/Xuống) |
| 🤟 **Ngón cái + Ngón trỏ + Ngón út** | Tăng / Giảm âm lượng hệ thống |
| ✊ **Nắm tay** | Tạm dừng tracking (Pause) |

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Ứng Dụng

Mở Terminal hoặc Command Prompt tại thư mục dự án và chạy:

```bash
run.bat
```
