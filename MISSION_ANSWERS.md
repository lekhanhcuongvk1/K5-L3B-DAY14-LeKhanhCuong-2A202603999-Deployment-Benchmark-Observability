# Day 14 Lab — Mission Answers

Bài đang ở CP0; chưa có kết quả thực nghiệm cho Part 1–7. Tiến độ và lỗi môi trường được ghi trong [LAB_PROGRESS.md](LAB_PROGRESS.md).

## AI log

### Phiên chuẩn bị — CP0

- Yêu cầu: đọc repo và yêu cầu bài lab, thực hiện từng checkpoint, commit trên nhánh `cuonglk`.
- Hỗ trợ của Codex: đọc các tài liệu quy định K5 và bản khung Part 6; tạo nhánh; khởi động Docker Desktop; kiểm tra phiên bản Python, Docker, Compose và distro WSL; thử chạy hello-world; ghi lại lỗi thực tế và lộ trình nghiệm thu.
- Kiểm tra do Codex thực hiện: Docker Engine đã phản hồi; tải hello-world bị HTTP 429 từ Docker Hub; WSL chỉ có distro nội bộ docker-desktop.
- Phần người học tự sửa/tự kiểm tra: chưa thực hiện trong phiên này; cần hoàn tất Ubuntu WSL2 và xử lý tải image. Chưa xác nhận checkpoint nào hoàn thành.

### Phiên tiếp theo — cài Ubuntu WSL2

- Yêu cầu: Codex tự thực hiện cài đặt thay người học.
- Hỗ trợ và kiểm tra của Codex: cài thành công Ubuntu WSL2, tạo user `cuonglk` chưa đặt mật khẩu, cấu hình user mặc định; kiểm tra Python `3.14.4` và `os.name=posix`.
- Trở ngại còn lại: Ubuntu chưa được bật Docker WSL Integration; thử tải hello-world trên Windows vẫn bị Docker Hub trả HTTP 429. Công cụ UI chưa điều khiển được cửa sổ Docker đang thu nhỏ.
- Người học chưa tự kiểm tra; CP0 vẫn chưa được đánh dấu hoàn thành.
