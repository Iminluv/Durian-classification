# Hệ Thống Phân Loại Sầu Riêng Tự Động — Hướng Dẫn Sử Dụng (Operator Guide)

Tài liệu này hướng dẫn cách vận hành ứng dụng phân loại sầu riêng trên máy tính.

---

## 1. Khởi Động Hệ Thống

1. **Kiểm tra kết nối**:
   - Đảm bảo camera công nghiệp (USB/RTSP) đã được cấp nguồn và kết nối ổn định.
   - Kiểm tra bộ điều khiển relay USB đã được cắm vào cổng USB của máy tính điều khiển.
2. **Khởi động ứng dụng**:
   - Tìm biểu tượng ứng dụng Durian Classifier trên màn hình Desktop.
   - Nhấn đúp chuột để mở ứng dụng. Dịch vụ backend FastAPI sẽ tự động khởi chạy ngầm đi kèm.

---

## 2. Các Thành Phần Trên Bảng Điều Khiển

Giao diện chính được chia thành các phân khu chức năng:
- **Video trực tiếp (Live Camera Feed)**: Hiển thị hình ảnh thời gian thực từ camera. Các lỗi phát hiện (`crack` - nứt, `dark_spot` - đốm đen, `fungus` - nấm bệnh, `thorn_split` - bể gai, `reject` - loại bỏ) được đóng khung màu tương ứng.
- **Phân Hạng Hiện Tại (Current Grade)**: Hiển thị chữ cái phân hạng kích thước lớn `A`, `B`, `C` hoặc `REJECT` dựa trên chất lượng quả đang quét.
  - Một biểu ngữ cảnh báo màu đỏ sẽ nhấp nháy trên màn hình khi phát hiện lỗi nghiêm trọng (Nấm bệnh hoặc Reject).
- **Thanh đo mức độ tin cậy**: Thể hiện độ tin cậy của thuật toán đối với từng loại khuyết tật.
- **Thống kê sản lượng & Nhật ký**: Đếm số lượng quả đã chạy theo từng hạng và liệt kê nhật ký phân loại gần đây.

---

## 3. Quản Lý Lô Phân Loại

Để bắt đầu một phiên phân loại:
1. Nhấp chọn tab **Quản Lý Lô** (Batches) trên thanh menu bên trái.
2. Nhập **Mã Lô** (Batch ID) (Ví dụ: `BATCH_V1_001`) và **Mã Kỹ Thuật Viên** (Operator ID).
3. Chọn cấu hình **Điểm Chuẩn** (Benchmark) tương ứng.
4. Nhấn **Bắt Đầu Lô** (Start Batch) để kích hoạt ghi chép dữ liệu.
5. Nhấn **Kết Thúc Lô** (Stop Batch) khi hoàn thành phiên phân loại. Dữ liệu chỉ được ghi vào database SQLite khi lô đang hoạt động.

---

## 4. Cấu Hình Điểm Chuẩn Phân Hạng (Benchmark Profiles)

Bạn có thể chỉnh sửa quy tắc phân hạng trái cây:
1. Nhấp chọn tab **Cấu Hình Điểm Chuẩn** (Benchmarks).
2. Chọn một cấu hình sẵn có để chỉnh sửa, hoặc nhấn **Tạo Điểm Chuẩn Mới** (New Benchmark).
3. Thiết lập thông số cho từng loại lỗi:
   - **Số Lượng Tối Đa A, B, C**: Giới hạn số lượng khuyết tật tối đa xuất hiện trên vỏ để đạt được hạng tương ứng.
   - **Tỷ lệ diện tích tối đa (Max Area Ratio)**: Tỷ lệ phần trăm diện tích lỗi tối đa chiếm trên bề mặt quả.
   - **Bắt Buộc Loại (Force Reject)**: Đánh dấu ô này để lập tức loại quả (Grade Reject) nếu xuất hiện lỗi này.
4. Nhấn **Lưu** để áp dụng thay đổi ngay lập tức ở thời gian thực.

---

## 5. Lịch Sử & Xuất Báo Cáo

1. Chọn tab **Lịch Sử & Báo Cáo** (History & Reports).
2. Nhập **Mã Lô** cần tìm kiếm vào thanh tìm kiếm.
3. Bảng dữ liệu hiển thị mốc thời gian, phân hạng, lỗi phát hiện và độ tin cậy.
4. Nhấn **Tải Báo Cáo Excel** hoặc **Tải Báo Cáo PDF** để tải về các file báo cáo tổng hợp thống kê.

---

## 6. Cập Nhật Mô Hình OTA

Khi có mô hình AI mới được huấn luyện xong, một thông báo sẽ xuất hiện trong tab **Cài Đặt Hệ Thống** (Settings).
- Chỉ số so sánh mô hình mới và mô hình cũ (Độ thu hồi - Recall, Độ chính xác - mAP@50, Độ trễ - Latency) được hiển thị song song.
- Nhấn **Chấp Nhận Cập Nhật** để nạp trọng số mô hình mới ngay lập tức.
- Nhấn **Từ Chối Cập Nhật** để giữ nguyên mô hình cũ và xóa bản cập nhật tạm.
