# Deployment Information — CP6

**Trạng thái:** đã chuẩn bị cấu hình; chưa deploy, chưa có URL public hoặc ảnh cloud. CP6 chưa hoàn thành. Cần người học đăng nhập và cho phép truy cập tài khoản Render qua kết nối Render trong ChatGPT.

## Cấu hình sẵn sàng triển khai

- Platform dự kiến: Render, web Free và Key Value Free, cùng region Singapore.
- Repository branch: `cuonglk`.
- Blueprint path: `06-lab-complete/render.yaml`.
- Service root: `06-lab-complete`, Docker context `.`, Dockerfile `./Dockerfile`. Không dùng Dockerfile Go ở gốc repo.
- Web service: `day14-agent-cuonglk`; datastore: `day14-cache-cuonglk`.
- `AGENT_API_KEY` được Render tự sinh; `REDIS_URL` lấy từ connectionString nội bộ của datastore. Không copy credential vào tài liệu hoặc git.

File Blueprint khai báo sẵn cả hai service để tránh thiếu Redis khi deploy. Theo [Render Blueprint reference](https://render.com/docs/blueprint-spec), service Key Value dùng type `keyvalue`, biến môi trường có thể tham chiếu `fromService.connectionString`, còn Docker context tính tương đối với `rootDir`.

Theo [giới hạn Render Free](https://render.com/docs/free), Free Key Value không bền dữ liệu khi datastore restart, và mỗi workspace chỉ có một instance Free Key Value. Đây là giới hạn của triển khai lab; quota ngày/tháng cần datastore bền vững khi vận hành thật. Chưa tạo tài nguyên hoặc phát sinh phí cloud trong phiên chuẩn bị này.

## Biến môi trường đã khai báo trong config (chưa xác nhận đã đặt trên cloud)

| Biến | Nguồn |
| --- | --- |
| PORT | Platform cung cấp, Docker CMD đọc động |
| ENVIRONMENT | production |
| AGENT_API_KEY | Render generateValue, không lưu giá trị trong repo |
| REDIS_URL | Tham chiếu datastore nội bộ |
| RATE_LIMIT_PER_MINUTE | 10 |
| DAILY_BUDGET_USD | 1 |
| MONTHLY_BUDGET_USD | 10 |
| LOG_LEVEL | INFO |

## Kiểm tra sau khi có URL

Đặt `BASE` là URL thật và `AGENT_API_KEY` là secret trong môi trường terminal riêng, rồi chạy từ gốc repo:

```bash
python scripts/check_public.py
```

Script chỉ lưu kết quả HTTP/body và URL, không lưu key. CP6 chỉ được đánh dấu hoàn thành khi `/health` 200, `/ready` 200, JSON POST `/ask` thiếu key 401, có key 200. Bằng chứng sẽ được ghi vào `evidence/cp6-public.json` sau khi kiểm tra thật thành công.

## Screenshots cần thu sau triển khai

- `screenshots/dashboard.png`: dashboard cloud, che mọi credential.
- `screenshots/running.png`: service chạy thành công.
- `screenshots/test.png`: kết quả bốn kiểm tra HTTP.

Chưa có các ảnh này; không dùng ảnh mẫu hoặc ảnh dựng để thay bằng chứng.

## Railway thay thế

`06-lab-complete/railway.toml` được giữ đúng hợp đồng bài lab. [Tài liệu Railway hiện tại](https://docs.railway.com/config-as-code) cho biết config-as-code TOML/JSON cũ đã deprecated và service mới không còn opt-in; nếu chọn Railway phải kiểm tra/migrate cấu hình theo nền tảng trước khi deploy. Render Blueprint là phương án được chuẩn bị cho CP6 trong phiên này.
