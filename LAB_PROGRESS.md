# Tiến độ Day 14

## CP0 — Setup: hoàn thành

- Repo đã có tên theo mẫu K5 và remote cá nhân.
- Nhánh làm bài: `cuonglk`.
- Python Windows: `3.11.4`.
- Docker Desktop đã được khởi động; Docker Engine: `29.1.5`.
- Docker Compose: `v5.0.1`.
- `docker run --rm hello-world` chưa thành công: Docker Hub trả `429 Too Many Requests` khi lấy manifest.
- Ubuntu WSL2 đã cài thành công bằng `wsl --install -d Ubuntu --no-launch`.
- Đã tạo user cục bộ `cuonglk` (chưa đặt mật khẩu) và cấu hình user mặc định trong `/etc/wsl.conf`.
- Python Ubuntu: `3.14.4`; kiểm tra `os.name` trả `posix`.
- Docker CLI trong Ubuntu báo chưa bật WSL Integration. Đã thử mở Docker Desktop bằng công cụ UI nhưng cửa sổ đang thu nhỏ và công cụ không lấy được cửa sổ để thao tác.

### Kiểm tra lại sau khi người học bật WSL Integration

- `wsl -d Ubuntu --exec id`: user `cuonglk`, thuộc nhóm `docker`.
- `wsl -d Ubuntu --exec docker version`: client Linux và Engine `29.1.5` phản hồi thành công.
- `wsl -d Ubuntu --exec docker run --rm hello-world`: exit code 0, in `Hello from Docker!`; lỗi tải image HTTP 429 đã hết trong lần kiểm tra này.
- Cài Python 3.11 riêng bằng uv để tương thích requirements đã ghim của bài; không đổi Python hệ thống Ubuntu.

## Lộ trình và điều kiện nghiệm thu

Áp dụng README và CHECKPOINTS dành cho K5 khi có khác biệt với CODE_LAB hoặc checklist cũ.

| Checkpoint | Sản phẩm cần có | Trạng thái |
| --- | --- | --- |
| CP0 | Python trong WSL2, Docker chạy được hello-world | Hoàn thành |
| CP1 | Part 1: anti-pattern, gọi develop, bảng so sánh | Hoàn thành; evidence/cp1.json |
| CP2 | Part 2: chạy container, số MB thực đo, test Nginx | Hoàn thành; evidence/cp2.json; HTTP :8082 |
| CP3 | Part 4: bằng chứng HTTP 401/200/429, giải thích cost guard | Hoàn thành; evidence/cp3.json và cp3-http.txt |
| CP4 | Part 5: health/readiness, shutdown, test 3 instance dùng Redis | Hoàn thành; evidence/cp4.json và cp4-stateless.txt |
| CP5 | Hoàn thiện `06-lab-complete/`, script gốc PASS 12/12 | Hoàn thành; 43/43 checks; evidence/cp5-production-ready.txt |
| CP6 | Deploy agent Part 6 cùng Redis, URL public và ảnh thật | Live trên main/283bdca; đủ 4 HTTP checks đạt; còn file screenshot trong repo |
| CP7 | Load test, eval v1/v2/fixed, quality gate, report JSON | Hoàn thành; v2 fixed 23/23, 0 regression; BENCHMARK_REPORT.md và reports/ |
| CP8 | Grafana, Jaeger, ít nhất 2 alert cùng firing, CSV scale, đóng gói | Bị chặn khi tải image: Docker Hub HTTP 429; evidence/cp8-startup.txt |

Không sửa script chấm hoặc golden dataset. Không ghi số đo, URL hay ảnh giả. Không commit secret. Mỗi checkpoint hoàn thành có một commit riêng; commit setup này chỉ ghi nhận bước chuẩn bị còn bị chặn.

## Cần người học can thiệp để tiếp tục CP8

1. Đăng nhập Docker Desktop bằng tài khoản Docker Hub của mình, rồi thử `docker pull nginx:1.28-alpine`. Nếu đã đăng nhập mà vẫn 429, báo lại kết quả; chưa thể kết luận việc đăng nhập chắc chắn khắc phục giới hạn registry.
2. Bổ sung ba ảnh cloud vào `screenshots/` theo hướng dẫn trong thư mục đó. Bốn kiểm tra public đã PASS, nhưng chưa có các file ảnh cần nộp.

Đã thử khởi động stack observability từ Windows và Ubuntu WSL2, đều gặp HTTP 429 khi lấy manifest của Locust hoặc Nginx. Chưa có container observability chạy, chưa có số đo hay ảnh CP8. Không đánh dấu checkpoint hoàn thành. Remote GitHub Actions chưa xác minh được vì API GitHub cũng trả lỗi rate limit; lệnh quality gate tương đương đã PASS ở local.
