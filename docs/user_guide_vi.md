# Hệ Thống Phân Loại Sầu Riêng Tự Động — Hướng Dẫn Vận Hành (Operator Guide)

Tài liệu này hướng dẫn chi tiết quy trình vận hành và sử dụng ứng dụng **Phát Hiện Khuyết Tật & Phân Loại Chất Lượng Sầu Riêng Tự Động** trên máy tính điều khiển công nghiệp và trình duyệt web.

---

## 1. Chuẩn Bị & Khởi Động Hệ Thống

### 1.1 Kiểm Tra Phần Cứng Trước Khi Vận Hành
1. **Camera công nghiệp**: Đảm bảo camera (USB hoặc RTSP) đã được cố định chắc chắn phía trên băng chuyền và hệ thống đèn LED chiếu sáng đạt chuẩn (tối thiểu 500 lux, không nhấp nháy).
2. **Bộ điều khiển Relay USB**: Kiểm tra mạch relay 4 kênh (VID `0x16c0`, PID `0x05df`) đã được cắm vào cổng USB của máy tính điều khiển.
3. **Cửa gạt phân loại khí nén**: Đảm bảo nguồn khí nén đã bật và các xi-lanh gạt phân loại hoạt động trơn tru theo các kênh relay 1–4.

### 1.2 Khởi Động Ứng Dụng
- **Ứng dụng Desktop (Tauri App)**:
  - Nhấn đúp chuột vào biểu tượng **Durian Classifier** trên màn hình Desktop hoặc khởi chạy qua lệnh:
    ```bash
    cd ui/src-tauri && cargo tauri dev
    ```
  - Dịch vụ backend FastAPI sẽ tự động khởi chạy và thiết lập kết nối WebSocket với giao diện điều khiển.
- **Ứng dụng Web Workflow (Kiểm tra từ xa / QA)**:
  - Khởi động máy chủ web:
    ```bash
    python workflow_app/app.py
    ```
  - Truy cập địa chỉ `http://127.0.0.1:8000` trên trình duyệt web.

---

## 2. Các Phân Khu Chức Năng Trên Bảng Điều Khiển

Giao diện chính được thiết kế trực quan và cập nhật dữ liệu thời gian thực:

```
┌────────────────────────────────────────────────────────┐
│ [VIDEO TRỰC TIẾP]                 [HẠNG HIỆN TẠI]      │
│ Khung nhận diện thời gian thực:   ┌──────────────────┐ │
│ - Nứt vỏ / crack (Cam)            │        A         │ │
│ - Đốm đen / dark_spot (Nâu)       │     (Hạng A)     │ │
│ - Nấm bệnh / fungus (Vàng)        └──────────────────┘ │
│ - Bể gai / thorn_split (Hổ phách) [ĐỘ TIN CẬY AI]      │
│ - Trái loại / reject (Đỏ)         Nứt: 85%  Nấm: 0%    │
├────────────────────────────────────────────────────────┤
│ [BẢNG ĐẾM SỐ LƯỢNG LÔ]                                 │
│ Tổng: 1.420 | Hạng A: 920 | Hạng B: 340 | C: 120 | R: 40
├────────────────────────────────────────────────────────┤
│ [NHẬT KÝ PHÂN LOẠI THỜI GIAN THỰC]                     │
│ 14:22:05 - Trái #1420 -> Hạng A (Không có lỗi)         │
│ 14:22:02 - Trái #1419 -> Hạng B (1x đốm đen nhỏ)       │
└────────────────────────────────────────────────────────┘
```

1. **Khung Video Trực Tiếp (Live Feed Canvas)**: Hiển thị hình ảnh từ camera với các hộp nhận diện lỗi (bounding box), tên loại khuyết tật và độ tin cậy.
2. **Huy Hiệu Phân Hạng Hiện Tại (Grade Badge)**: Hiển thị chữ cái lớn `A`, `B`, `C` hoặc `REJECT` tương ứng với chất lượng quả đang quét.
   - **Cảnh báo nhấp nháy**: Biểu ngữ đỏ sẽ nhấp nháy cảnh báo nếu quả bị nhiễm nấm (`fungus`) hoặc bị đánh rớt (`REJECT`).
3. **Thanh Đo Mức Độ Tin Cậy**: Thể hiện tỷ lệ tin cậy và tỷ lệ diện tích bề mặt của từng loại khuyết tật.
4. **Bộ Đếm Sản Lượng Lô**: Thống kê tổng số lượng quả và số lượng từng phân hạng trong phiên làm việc.
5. **Nhật Ký Sự Kiện**: Liệt kê mốc thời gian và chi tiết quyết định phân hạng của từng quả.

---

## 3. Quản Lý Lô Phân Loại (Batch Management)

Để ghi nhận và lưu trữ dữ liệu phân loại cho từng lô hàng xuất xưởng:

1. Chọn tab **Quản Lý Lô** (Batches) trên thanh điều hướng bên trái.
2. Nhập **Mã Lô** (Ví dụ: `LO_SAURIENG_20260525_01`).
3. Nhập **Mã Kỹ Thuật Viên** (Ví dụ: `KTV_NGUYEN_02`).
4. Chọn cấu hình **Điểm Chuẩn Phân Hạng** (Ví dụ: `Standard QC v1`).
5. Nhấn **Bắt Đầu Lô (Start Batch)**:
   - Trạng thái chuyển sang màu xanh lá (`HOẠT ĐỘNG`).
   - Mọi quả đi qua camera sẽ được ghi nhận vào cơ sở dữ liệu SQLite cục bộ.
   - Bộ điều khiển relay sẽ kích hoạt xi-lanh gạt quả theo từng hạng.
6. Nhấn **Kết Thúc Lô (Stop Batch)** khi hoàn tất phiên phân loại:
   - Hệ thống tổng kết số liệu và khóa dữ liệu lô.

---

## 4. Cấu Hình Điểm Chuẩn Phân Hạng (Benchmark Profiles)

Người quản lý chất lượng (QA) có thể tinh chỉnh quy tắc phân hạng mà không cần huấn luyện lại mô hình AI:

1. Chọn tab **Cấu Hình Điểm Chuẩn** (Benchmarks).
2. Chọn một cấu hình cần chỉnh sửa hoặc nhấn **Tạo Điểm Chuẩn Mới**.
3. Thiết lập thông số cho từng loại lỗi:
   - **Số lượng tối đa A, B, C**: Số lượng khuyết tật tối đa cho phép xuất hiện trên một quả để đạt hạng tương ứng.
   - **Tỷ lệ diện tích tối đa (Max Area Ratio)**: Tỷ lệ phần trăm diện tích lỗi tối đa chiếm trên bề mặt quả (Ví dụ: `0.02` = 2%).
   - **Bắt Buộc Loại (Force Reject)**: Nếu đánh dấu, quả sẽ lập tức bị phân vào hạng `REJECT` nếu xuất hiện bất kỳ lỗi này (Ví dụ: nấm bệnh kiểm dịch).
4. Thiết lập **Quy Tắc Tổng Thể (Global Rules)**:
   - Giới hạn tổng số khuyết tật cộng dồn cho từng hạng.
   - Giới hạn tổng diện tích khuyết tật cộng dồn.
5. Nhấn **Lưu Điểm Chuẩn**: Quy tắc mới được áp dụng tức thì mà không cần khởi động lại ứng dụng.

---

## 5. Lịch Sử & Xuất Báo Cáo (History & Reports)

1. Chọn tab **Lịch Sử & Báo Cáo** (History & Reports).
2. Tìm kiếm lô phân loại theo **Mã Lô** hoặc khoảng thời gian.
3. Xem chi tiết danh sách từng quả đã quét kèm thông tin loại lỗi, độ tin cậy và phân hạng cuối.
4. Xuất tài liệu nghiệm thu & chứng từ xuất khẩu:
   - **Tải Báo Cáo Excel (`.xlsx`)**: Bảng tính tổng hợp đa biểu mẫu kèm biểu đồ phân bố lỗi và nhật ký chi tiết từng quả.
   - **Tải Báo Cáo PDF (`.pdf`)**: Chứng thư kiểm định chất lượng định dạng chuẩn in ấn để phục vụ thông quan xuất khẩu.

---

## 6. Cập Nhật Mô Hình AI Qua Mạng (OTA Model Updates)

Khi luồng huấn luyện chạy ngầm (Celery) hoàn thành một phiên huấn luyện với dữ liệu mới:

1. Một biểu ngữ thông báo xuất hiện trong tab **Cài Đặt Hệ Thống**: **"Có Bản Cập Nhật Mô Hình AI Mới Cần Phê Duyệt"**.
2. Kiểm tra bảng so sánh chỉ số KPI giữa mô hình cũ và mô hình mới:
   - **mAP@50**: Yêu cầu $\ge 70\%$
   - **Độ thu hồi nấm bệnh (Fungus Recall)**: Yêu cầu $\ge 85\%$
   - **Độ thu hồi hàng loại (Reject Recall)**: Yêu cầu $\ge 85\%$
   - **Độ trễ xử lý (Latency)**: Yêu cầu $< 100\text{ ms}$ (CoreML) / $< 200\text{ ms}$ (OpenVINO)
3. Lựa chọn thao tác:
   - **Chấp Nhận Cập Nhật (Approve)**: Nạp ngay bộ trọng số mới vào luồng nhận diện trực tiếp mà không cần dừng dây chuyền.
   - **Từ Chối Cập Nhật (Reject)**: Hủy bỏ bản cập nhật và tiếp tục sử dụng mô hình hiện tại.

---

## 7. Hướng Dẫn Xử Lý Sự Cố Thường Gặp

| Hiện Tượng | Nguyên Nhân | Cách Xử Lý |
|---|---|---|
| **Màn hình video bị đen** | Camera bị ngắt kết nối hoặc sai cổng | Kiểm tra cáp USB; kiểm tra lại `"usb_device_id"` trong `config/camera.json`. |
| **Cửa gạt relay không nhảy** | Mạch relay lỏng cổng USB | Kiểm tra đèn tín hiệu relay; chuyển `"relay_mock": false` trong `config/app.json`. |
| **Không ghi nhận lịch sử** | Chưa nhấn bắt đầu lô | Vào tab **Quản Lý Lô** và nhấn **Bắt Đầu Lô**. |
| **Phân loại quá khắt khe** | Điểm chuẩn đang đặt ngưỡng thấp | Vào tab **Cấu Hình Điểm Chuẩn** để điều chỉnh lại số lượng lỗi cho phép. |
