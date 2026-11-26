# Deployment Information — CP6

**Trạng thái:** service đã deploy thành công trên Render từ nhánh `main`, commit `283bdca` (theo ảnh deploy người học cung cấp). Đã xác minh trực tiếp ba endpoint không cần key; còn kiểm tra `/ask` có key và đóng gói đủ ảnh trước khi xác nhận CP6 hoàn thành.

## Public URL và kết quả đã xác minh

https://k5-l3b-day14-lekhanhcuong-2a202603999.onrender.com

Kiểm tra lúc **15:45 ngày 26/11/2026 (GMT+7)**, bằng script gửi JSON hợp lệ:

| Kiểm tra | HTTP | Body |
| --- | ---: | --- |
| GET /health | 200 | `{"status":"ok"}` |
| GET /ready | 200 | `{"ready":true}` |
| POST /ask thiếu API key | 401 | `{"detail":"Missing or invalid API key"}` |
| POST /ask có API key | Chưa kiểm tra | Chờ key trong file riêng trên máy |

Bằng chứng thật: [evidence/cp6-public-partial.json](evidence/cp6-public-partial.json). File ghi rõ `complete=false`, không coi ba kiểm tra là hoàn thành cả checkpoint. Readiness 200 xác nhận agent ping Redis thành công ở thời điểm kiểm tra.

## Cấu hình triển khai

- Platform: Render; người học tạo Web Service trực tiếp trên dashboard và cấu hình Redis/Key Value tại Singapore.
- Nhánh triển khai: `main`; nhánh làm bài và commit tiếp: `cuonglk`.
- Blueprint tham khảo trong repo: `06-lab-complete/render.yaml` (không phải cách tạo service thực tế trong lần deploy này).
- Service root: `06-lab-complete`, Docker context `.`, Dockerfile `./Dockerfile`. Không dùng Dockerfile Go ở gốc repo.
- Tên service hiển thị theo tên repo; hostname public được ghi ở trên. Tên datastore thực tế chưa được xác nhận, không suy ra từ URL nội bộ.
- `AGENT_API_KEY` đặt trên Render; `REDIS_URL` dùng địa chỉ nội bộ của datastore. Không copy credential vào tài liệu hoặc git.

File Blueprint khai báo sẵn cả hai service để tránh thiếu Redis khi deploy. Theo [Render Blueprint reference](https://render.com/docs/blueprint-spec), service Key Value dùng type `keyvalue`, biến môi trường có thể tham chiếu `fromService.connectionString`, còn Docker context tính tương đối với `rootDir`.

Theo [giới hạn Render Free](https://render.com/docs/free), Free Key Value không bền dữ liệu khi datastore restart, và mỗi workspace chỉ có một instance Free Key Value. Đây là giới hạn của triển khai lab; quota ngày/tháng cần datastore bền vững khi vận hành thật. Ảnh cấu hình người học cung cấp hiển thị Web Service $0/tháng; chưa kiểm tra billing workspace.

## Biến môi trường trên dashboard (theo ảnh người học cung cấp)

| Biến | Nguồn |
| --- | --- |
| PORT | 8000, Docker CMD đọc động |
| ENVIRONMENT | production |
| AGENT_API_KEY | Giá trị riêng trên Render; chưa dùng để kiểm tra xác thực thành công |
| REDIS_URL | URL Redis nội bộ; /ready đã trả 200 |
| RATE_LIMIT_PER_MINUTE | 10 |
| DAILY_BUDGET_USD | 1 |
| MONTHLY_BUDGET_USD | 10 |
| LOG_LEVEL | INFO |

## Hoàn tất kiểm tra có xác thực

File local `06-lab-complete/.env` đã được chuẩn bị với BASE thật và ô AGENT_API_KEY trống. Người học điền key hiện tại của Render vào file riêng này; `.gitignore` đã xác nhận loại trừ file. Không gửi key qua chat hoặc đưa ảnh chứa key vào bài nộp. Sau đó chạy trong môi trường Python lab từ gốc repo:

```bash
python scripts/check_public.py --env-file 06-lab-complete/.env
```

Script chỉ lưu kết quả HTTP/body và URL, không lưu key. CP6 chỉ được đánh dấu hoàn thành khi `/health` 200, `/ready` 200, JSON POST `/ask` thiếu key 401, có key 200 và có đủ ảnh yêu cầu. Kết quả kiểm tra đủ bốn endpoint sẽ được ghi vào `evidence/cp6-public.json`; chỉ `passed=true` khi cả bốn status đúng.

## Screenshots cần thu sau triển khai

- `screenshots/dashboard.png`: dashboard cloud, che mọi credential.
- `screenshots/running.png`: service chạy thành công.
- `screenshots/test.png`: kết quả bốn kiểm tra HTTP.

Người học đã gửi ảnh deploy succeeded trong chat (commit `283bdca`, lúc 15:41:29 GMT+7 ngày 26/11/2026), nhưng chưa có file ảnh trong thư mục screenshots của repo. Không dùng ảnh mẫu hoặc ảnh dựng để thay bằng chứng; không lưu ảnh môi trường có API key hiện rõ.

## Railway thay thế

`06-lab-complete/railway.toml` được giữ đúng hợp đồng bài lab. [Tài liệu Railway hiện tại](https://docs.railway.com/config-as-code) cho biết config-as-code TOML/JSON cũ đã deprecated và service mới không còn opt-in; nếu chọn Railway phải kiểm tra/migrate cấu hình theo nền tảng trước khi deploy. Render Blueprint là phương án được chuẩn bị cho CP6 trong phiên này.
