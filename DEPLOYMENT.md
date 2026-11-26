# Deployment Information — CP6

**Status:** CP6 complete: public deployment verified, four HTTP checks passed, three authentic screenshots included. See the timestamped evidence below.

## Public URL và kết quả đã xác minh

https://k5-l3b-day14-lekhanhcuong-2a202603999.onrender.com

Kiểm tra đầy đủ lúc **15:49 ngày 26/11/2026 (GMT+7)**, bằng script gửi JSON hợp lệ và đọc key từ file .env riêng:

| Kiểm tra | HTTP | Body |
| --- | ---: | --- |
| GET /health | 200 | `{"status":"ok"}` |
| GET /ready | 200 | `{"ready":true}` |
| POST /ask thiếu API key | 401 | `{"detail":"Missing or invalid API key"}` |
| POST /ask có API key | 200 | Có answer và usage; không lưu key |

Bằng chứng đầy đủ: [evidence/cp6-public.json](evidence/cp6-public.json), có `complete=true`, `passed=true`. Bằng chứng ba kiểm tra trước đó giữ riêng ở `evidence/cp6-public-partial.json`. Readiness 200 xác nhận agent ping Redis thành công ở thời điểm kiểm tra.

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
| AGENT_API_KEY | Giá trị riêng trên Render; đã kiểm tra xác thực thành công, không lưu trong git |
| REDIS_URL | URL Redis nội bộ; /ready đã trả 200 |
| RATE_LIMIT_PER_MINUTE | 10 |
| DAILY_BUDGET_USD | 1 |
| MONTHLY_BUDGET_USD | 10 |
| LOG_LEVEL | INFO |

## Hoàn tất kiểm tra có xác thực

Người học đã điền key hiện tại vào file local `06-lab-complete/.env`; `.gitignore` đã xác nhận loại trừ file. Không gửi key qua chat hoặc đưa ảnh chứa key vào bài nộp. Chạy lại trong môi trường Python lab từ gốc repo:

```bash
python scripts/check_public.py --env-file 06-lab-complete/.env
```

Script chỉ lưu kết quả HTTP/body và URL, không lưu key. CP6 chỉ được đánh dấu hoàn thành khi `/health` 200, `/ready` 200, JSON POST `/ask` thiếu key 401, có key 200 và có đủ ảnh yêu cầu. Kết quả kiểm tra đủ bốn endpoint sẽ được ghi vào `evidence/cp6-public.json`; chỉ `passed=true` khi cả bốn status đúng.

## Screenshots (complete)

- [dashboard.png](screenshots/dashboard.png): actual Render service dashboard.
- [running.png](screenshots/running.png): successful Live deployment of commit `283bdca`.
- [test.png](screenshots/test.png): browser displaying the actual JSON report with HTTP 200/200/401/200; no API key.

Original Render JPEG captures are retained in evidence/. CP6 is complete. Deployment hash above refers to the version verified at capture time.

## Railway thay thế

`06-lab-complete/railway.toml` được giữ đúng hợp đồng bài lab. [Tài liệu Railway hiện tại](https://docs.railway.com/config-as-code) cho biết config-as-code TOML/JSON cũ đã deprecated và service mới không còn opt-in; nếu chọn Railway phải kiểm tra/migrate cấu hình theo nền tảng trước khi deploy. Render Blueprint là phương án được chuẩn bị cho CP6 trong phiên này.
