# Báo cáo triển khai — CP6

Ứng dụng đã chạy trên Render và vượt qua cả bốn kiểm tra HTTP. Báo cáo này ghi lại cấu hình, kết quả kiểm tra và ảnh chụp của lần triển khai đã xác minh.

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

- Nền tảng: Render, gồm Web Service và Redis/Key Value tại Singapore.
- Nhánh triển khai: `main`; nhánh phát triển: `cuonglk`.
- Blueprint tham khảo trong repo: `06-lab-complete/render.yaml` (không phải cách tạo service thực tế trong lần deploy này).
- Service root: `06-lab-complete`, Docker context `.`, Dockerfile `./Dockerfile`. Không dùng Dockerfile Go ở gốc repo.
- Tên service hiển thị theo tên repo; hostname public được ghi ở trên. Tên datastore thực tế chưa được xác nhận, không suy ra từ URL nội bộ.
- `AGENT_API_KEY` đặt trên Render; `REDIS_URL` dùng địa chỉ nội bộ của datastore. Giá trị credential được lưu ngoài Git.

File Blueprint khai báo sẵn cả hai service để tránh thiếu Redis khi deploy. Theo [Render Blueprint reference](https://render.com/docs/blueprint-spec), service Key Value dùng type `keyvalue`, biến môi trường có thể tham chiếu `fromService.connectionString`, còn Docker context tính tương đối với `rootDir`.

Theo [giới hạn Render Free](https://render.com/docs/free), Free Key Value không bền dữ liệu khi datastore restart, và mỗi workspace chỉ có một instance Free Key Value. Đây là giới hạn của triển khai lab; quota ngày/tháng cần datastore bền vững khi vận hành thật. Ảnh cấu hình triển khai hiển thị Web Service $0/tháng; chưa kiểm tra billing workspace.

## Biến môi trường đã cấu hình

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

## Cách kiểm tra lại

Script đọc key từ `06-lab-complete/.env`, là file đã được Git loại trừ. Từ thư mục gốc repo, chạy trong môi trường Python của lab:

```bash
python scripts/check_public.py --env-file 06-lab-complete/.env
```

Kết quả được lưu tại `evidence/cp6-public.json`, gồm URL, HTTP status và response body. Report hiện tại có `complete=true` và `passed=true`, tương ứng cả bốn kiểm tra đều đạt. Script không ghi API key vào output.

## Ảnh triển khai

- [Dashboard Render](screenshots/dashboard.png): service và trạng thái Live.
- [Deploy thành công](screenshots/running.png): phiên bản `283bdca` tại thời điểm kiểm tra.
- [Kết quả HTTP](screenshots/test.png): trình duyệt hiển thị report JSON với bốn mã 200/200/401/200.

Bản chụp Render gốc được giữ trong `evidence/`. Mã commit trong ảnh là phiên bản được xác minh lúc chụp; các commit báo cáo được bổ sung sau đó.

## Railway thay thế

`06-lab-complete/railway.toml` được giữ theo cấu trúc bài lab. [Tài liệu Railway hiện tại](https://docs.railway.com/config-as-code) cho biết config-as-code TOML/JSON cũ đã deprecated và service mới không còn opt-in. Vì vậy, triển khai mới trên Railway cần kiểm tra lại phương án cấu hình. Trong bài này, Render là nền tảng đã được sử dụng và xác minh.
