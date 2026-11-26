# Ảnh minh chứng cần nộp

Hiện chưa có file ảnh thật trong thư mục này. Không dùng ảnh dựng, ảnh mẫu hoặc ảnh có credential hiện rõ.

## CP6 — cần bổ sung từ Render và kết quả kiểm tra thật

- `dashboard.png`: dashboard service trên Render, thấy tên service và trạng thái.
- `running.png`: trang deploy thành công (Live), thấy commit triển khai.
- `test.png`: terminal chạy `python scripts/check_public.py --env-file 06-lab-complete/.env`, thấy bốn status 200 / 200 / 401 / 200. Command không in API key; chụp sau khi chạy thật, không chụp nội dung .env.

Ảnh deploy đã gửi trong chat chưa được lưu thành file trong repo. Không sử dụng ảnh Environment đã gửi trong chat vì ảnh đó hiển thị key.

## CP8 — chụp sau khi stack chạy được

- `grafana-dashboard.png`: dashboard khi có tải.
- `jaeger-slow-trace.png`: trace chậm, thấy span và thời gian.
- `jaeger-error-trace.png`: trace lỗi, thấy event exception.
- `prometheus-alert-firing.png`: trang Alerts thấy ít nhất hai alert cùng firing.
