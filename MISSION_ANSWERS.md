# Day 14 Lab — Mission Answers

CP0 đã hoàn thành: Python chạy trong Ubuntu WSL2 (`posix`), Docker Engine phản hồi và hello-world chạy thành công. Tiến độ được ghi trong [LAB_PROGRESS.md](LAB_PROGRESS.md).

## Part 1 — Localhost vs Production (CP1)

### Exercise 1.1 — Anti-patterns

Trong `01-localhost-vs-production/develop/app.py`:

1. Dòng 19–20 nhúng key giả và database URL có mật khẩu trong source; nếu là secret thật, Git history vẫn giữ lại sau khi xóa.
2. Dòng 23–24 cố định DEBUG và MAX_TOKENS; cùng artifact khó chạy ở các môi trường khác nhau.
3. Dòng 37 in API key ra log; người có quyền xem log cũng đọc được secret.
4. Không có `/health` và `/ready`; platform không phân biệt process còn sống với service sẵn sàng.
5. Dòng 56 bind `localhost`; container không nhận kết nối từ ngoài network namespace.
6. Dòng 57 cố định port 8000, không đọc PORT của nền tảng.
7. Dòng 58 bật reload cho mọi môi trường; reload là công cụ phát triển, làm phát sinh process giám sát không cần thiết khi deploy.
8. Chưa có lifecycle cleanup cho tài nguyên khi shutdown.

### Exercise 1.2 — Kết quả chạy thật

Chạy trong Ubuntu bằng Python 3.11.18; dùng uvicorn CLI để tránh reload khi tự động hóa. Tái hiện: `python scripts/check_examples.py cp1` sau khi kích hoạt môi trường lab.

- `POST /ask?question=Hello` → **200**, có `answer`.
- `POST /ask` với JSON → **422**, thiếu `query.question`, đúng lưu ý K5.
- Bản production: JSON `/ask` → **200**, `/health` → **200**, `/ready` → **200**.
- Header, body đầy đủ: [evidence/cp1.json](evidence/cp1.json).

### Exercise 1.3 — So sánh

| Feature | Develop | Production | Vì sao quan trọng? |
| --- | --- | --- | --- |
| Config | Giá trị cố định trong app.py | `Settings` đọc env trong config.py | Đổi staging/production mà không sửa source |
| Secrets | Source và log chứa key giả | Đọc env, log độ dài câu hỏi | Giảm nguy cơ lộ credential |
| Bind / port | localhost:8000 | HOST mặc định 0.0.0.0, PORT từ env | Nhận kết nối qua container/cloud |
| Health | Không có | `/health`, `/ready` | Liveness quyết định restart, readiness quyết định route traffic |
| Logging | print | logging với định dạng JSON | Dễ gom log và tìm event |
| Shutdown | Không có cleanup | lifespan startup/shutdown | Đóng kết nối sau khi hoàn thành request |

Ví dụ sửa cụ thể: `develop/app.py:57` dùng `port=8000`; `production/app.py` dùng `port=settings.port`, còn `production/config.py` đọc `os.getenv("PORT", "8000")`.

Nhận xét khi đọc code: bản mẫu production chưa phải thiết kế cuối cùng. Nó ghép JSON bằng chuỗi format nên message có dấu nháy có thể làm log không hợp lệ; `/ready` mới kiểm tra cờ startup. Khi import qua uvicorn CLI, signal handler tự đăng ký có thể ghi đè handler của uvicorn (runner phải giới hạn thời gian dọn process). CP5 cần formatter `json.dumps`, kiểm tra Redis thật và giữ cơ chế signal của server.

Stateless nghĩa là các instance chia sẻ state bên ngoài process; nếu lưu RAM thì request sau đến instance khác sẽ thiếu history. Dev/prod parity là giảm khác biệt runtime, dependency và dịch vụ phụ thuộc giữa môi trường phát triển và triển khai.

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

### Xác nhận CP0

- Người học xác nhận đã bật WSL Integration.
- Codex kiểm tra lại trong Ubuntu: user `cuonglk` thuộc nhóm docker, Docker client Linux kết nối Engine 29.1.5, hello-world chạy thành công. CP0 hoàn thành.
- Codex chuẩn bị script tái tạo môi trường Python 3.11 riêng; người học chưa tự chạy lại các kiểm tra này.

### CP1

- Yêu cầu: thực hiện checkpoint Localhost vs Production.
- Codex đọc code mẫu, viết phần phân tích và runner kiểm tra HTTP; chạy thật trên WSL2, lưu status/header/body trong `evidence/cp1.json`, không lưu log chứa key giả của ví dụ develop.
- Người học chưa tự sửa hoặc chạy lại; cần đọc các so sánh và giải thích được các điểm nêu trên khi Lab Coach hỏi.
