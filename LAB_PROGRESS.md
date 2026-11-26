# Tiến độ Day 14

## CP0 — Setup: đang chờ xử lý môi trường

- Repo đã có tên theo mẫu K5 và remote cá nhân.
- Nhánh làm bài: `cuonglk`.
- Python Windows: `3.11.4`.
- Docker Desktop đã được khởi động; Docker Engine: `29.1.5`.
- Docker Compose: `v5.0.1`.
- `docker run --rm hello-world` chưa thành công: Docker Hub trả `429 Too Many Requests` khi lấy manifest.
- `wsl --list --quiet` chỉ có `docker-desktop`; chưa có distro Linux dành cho việc chạy Python.

### Cần xử lý trước khi xác nhận CP0 hoàn thành

1. Cài Ubuntu WSL2 bằng `wsl --install -d Ubuntu`, mở Ubuntu và hoàn tất tạo tài khoản Linux.
2. Bật Docker Desktop → Settings → Resources → WSL Integration cho Ubuntu.
3. Đăng nhập Docker Desktop bằng tài khoản Docker Hub nếu có để xử lý giới hạn tải image, rồi chạy lại `docker run --rm hello-world`.
4. Trong Ubuntu, kiểm tra Python 3.11+ và `python3 -c "import os; print(os.name)"` trả `posix`.

## Lộ trình và điều kiện nghiệm thu

Áp dụng README và CHECKPOINTS dành cho K5 khi có khác biệt với CODE_LAB hoặc checklist cũ.

| Checkpoint | Sản phẩm cần có | Trạng thái |
| --- | --- | --- |
| CP0 | Python trong WSL2, Docker chạy được hello-world | Chưa hoàn thành |
| CP1 | Part 1: anti-pattern, gọi develop, bảng so sánh | Chưa làm |
| CP2 | Part 2: chạy container, số MB thực đo, test Nginx | Chưa làm |
| CP3 | Part 4: bằng chứng HTTP 401/200/429, giải thích cost guard | Chưa làm |
| CP4 | Part 5: health/readiness, shutdown, test 3 instance dùng Redis | Chưa làm |
| CP5 | Hoàn thiện `06-lab-complete/`, script gốc PASS 12/12 | Chưa làm |
| CP6 | Deploy agent Part 6 cùng Redis, URL public và ảnh thật | Chưa làm |
| CP7 | Load test, eval v1/v2/fixed, quality gate, report JSON | Chưa làm |
| CP8 | Grafana, Jaeger, ít nhất 2 alert cùng firing, CSV scale, đóng gói | Chưa làm |

Không sửa script chấm hoặc golden dataset. Không ghi số đo, URL hay ảnh giả. Không commit secret. Mỗi checkpoint hoàn thành có một commit riêng; commit setup này chỉ ghi nhận bước chuẩn bị còn bị chặn.
