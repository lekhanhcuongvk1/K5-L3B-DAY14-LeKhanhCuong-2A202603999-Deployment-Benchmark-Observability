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

## Part 2 — Docker (CP2)

### Exercise 2.1 — Dockerfile cơ bản

1. Base image: `python:3.11`, gồm Python và hệ điều hành nền; tag có thể thay đổi theo bản cập nhật.
2. Working directory: `/app`; các lệnh COPY/RUN và command làm việc từ đó.
3. Copy requirements trước source để layer cài dependency được tái dùng khi chỉ sửa code. `pip --no-cache-dir` không vô hiệu hóa Docker layer cache.
4. CMD cung cấp command/argument mặc định, bị thay bằng argument sau tên image khi `docker run`. ENTRYPOINT xác định chương trình chính; argument runtime thường được nối vào nó. Exec form giúp signal đến đúng process; shell phải dùng `exec` khi khởi động server.

### Exercise 2.2–2.3 — Build và số đo

Build từ gốc repo:

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images my-agent
```

| Image | SIZE từ docker images | Quy về MB thập phân để so sánh |
| --- | --- | ---: |
| my-agent:develop | 1.67GB | khoảng 1670 |
| my-agent:advanced | 240MB | khoảng 240 |

Theo số SIZE hiển thị đã làm tròn, giảm khoảng **85,63%**: `(1670 - 240) / 1670 × 100`.
Docker Engine này trả trường inspect `.Size` khác SIZE của `docker images`: lần lượt 426320129 và 57409181 byte. File bằng chứng lưu cả hai nguồn; không trộn chúng khi tính phần trăm. Bảng chính dùng `docker images` theo yêu cầu CP2.

Stage builder của production cài gcc/libpq-dev và pip dependencies vào `/root/.local`; runtime bắt đầu lại từ Python slim, chỉ copy packages/source, chạy user appuser. Runtime không mang theo các layer cài build tools. Slim base cũng góp phần giảm image; multi-stage không tự làm nhỏ nếu vẫn copy toàn bộ builder.

Container develop nhận `POST /ask?question=What%20is%20Docker` → 200. Output gốc của `docker images`, kích thước inspect và HTTP response: [evidence/cp2.json](evidence/cp2.json). Tái tạo kiểm tra: `python scripts/check_docker.py` khi stack CP2 đang chạy ở 8082.

### Exercise 2.4 — Compose stack

```mermaid
flowchart LR
    C[Client :8082] --> N[Nginx :80]
    N --> A[Agent :8000]
    A -. cấu hình REDIS_URL .-> R[Redis :6379]
    A -. cấu hình QDRANT_URL .-> Q[Qdrant :6333]
```

Compose tạo network nội bộ và volume cho Redis/Qdrant, đợi healthcheck của chúng trước khi bật agent. App mock mẫu chưa thực sự gọi Redis/Qdrant; đây là các dependency được khai báo cho kiến trúc mở rộng.

Windows từ chối bind host port 80. Đã sửa mapping thành `127.0.0.1:${HTTP_PORT:-8082}:80`, bỏ mapping 443 vì chưa cấu hình TLS. Qua Nginx `http://localhost:8082/health` → **200**; JSON `POST /ask` → **200**. Chạy bằng project `k5-day14-docker`, đã `down -v` sau khi lưu bằng chứng. Muốn mount dữ liệu ngoài image dùng bind mount hoặc named volume; `.dockerignore` loại venv/cache/secret để không đưa chúng vào build context.

## Part 3 — Cloud Deployment (CP6, chưa hoàn thành)

### Exercise 3.1 hoặc 3.2 — Triển khai

URL public: https://k5-l3b-day14-lekhanhcuong-2a202603999.onrender.com . Người học tạo Web Service trực tiếp trên Render, theo dõi nhánh `main` sau khi merge `cuonglk`; ảnh deploy xác nhận Live từ commit `283bdca` lúc 15:41:29 GMT+7 ngày 26/11/2026. Root `06-lab-complete`, Dockerfile và context tương ứng.

Codex kiểm tra đủ bốn endpoint lúc 15:49 GMT+7: `/health` **200**, `/ready` **200**, JSON `POST /ask` không key **401**, có key **200** với answer và usage. Key được đọc từ file .env riêng của người học, không ghi vào output hoặc git. Bằng chứng: [evidence/cp6-public.json](evidence/cp6-public.json), complete=true và passed=true. Còn đủ ảnh trong repo trước khi đánh dấu toàn bộ deliverable CP6 hoàn thành. Trạng thái chi tiết: [DEPLOYMENT.md](DEPLOYMENT.md).

### So sánh Railway và Render config

| Nội dung | railway.toml của Part 6 | render.yaml của Part 6 |
| --- | --- | --- |
| Phạm vi | Cấu hình build/deploy một service | Blueprint khai báo web service và datastore |
| Build | DOCKERFILE, Dockerfile | runtime docker, rootDir, dockerfilePath, dockerContext |
| Health | healthcheckPath /health | healthCheckPath /health |
| Secret | Đặt ngoài file trong platform env | generateValue cho API key; fromService cho REDIS_URL |
| Datastore | Tạo/link Redis trên nền tảng riêng | Khai báo Key Value cùng region ngay trong Blueprint |
| Định dạng | TOML | YAML |

Railway TOML giữ cho hợp đồng chấm; tài liệu Railway hiện tại đánh dấu cấu hình này deprecated, service mới cần phương án cấu hình mới. Render Blueprint được chuẩn bị để triển khai thực tế; không dùng các lệnh mẫu cũ một cách mặc định. Nguồn hiện hành và giới hạn free được liên kết trong DEPLOYMENT.md.

### Exercise 3.3 — Pipeline Cloud Run (đọc config, không deploy)

1. `cloudbuild.yaml` khai báo bước cài requirements và chạy pytest trên Python 3.11-slim.
2. Bước build phụ thuộc bước test, tạo Docker image gắn cả COMMIT_SHA lẫn latest và tái dùng layer cache từ latest.
3. Bước push đưa image lên registry, sau đó gcloud deploy image theo COMMIT_SHA lên Cloud Run ở asia-southeast1.
4. Deployment đặt giới hạn instance 1–10, CPU/memory/timeout, ENVIRONMENT và tham chiếu Secret Manager thay vì nhúng key.
5. `service.yaml` mô tả cấu hình service tương ứng: concurrency 80, env/secret và probe `/health`, `/ready`; phần này chỉ đọc và giải thích theo rubric K5.

Lưu ý khi đọc mẫu: shell test chưa bật `set -e`, nên câu echo cuối có thể che exit code pytest; muốn dùng thật phải bảo đảm lỗi test dừng pipeline. Chưa chạy hoặc tuyên bố deploy pipeline GCP.

## Part 4 — API Security (CP3)

### Exercise 4.1 — API key

`04-api-gateway/develop/app.py` dùng dependency `verify_api_key` đọc `X-API-Key` và so với env `AGENT_API_KEY`. Thiếu/sai key bị từ chối trước khi gọi LLM. Rotate bằng cách tạo key ngẫu nhiên mới, cập nhật env trên server và client rồi restart/redeploy; thu hồi key cũ, không ghi key vào source hay bài nộp.

Output thật từ `curl -i` (đầy đủ trong [evidence/cp3-http.txt](evidence/cp3-http.txt)):

```text
HTTP/1.1 401 Unauthorized
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

HTTP/1.1 200 OK
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Exercise 4.2–4.3 — JWT và rate limit

Lấy token ở `POST /auth/token` bằng tài khoản demo `student`, sau đó gửi Bearer token cho `/ask`. Token được ký HS256, chứa `sub`, `role`, `iat`, `exp`; server kiểm chữ ký và hạn dùng. Runner tạo JWT_SECRET ngẫu nhiên trong env và không ghi token ra file.

Kết quả vòng lặp: **10 request 200**, request thứ **11 trả 429**. [evidence/cp3.json](evidence/cp3.json) lưu dãy status. Một response tiếp theo từ curl:

```text
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

Code mẫu lưu deque timestamp trong RAM, loại request cũ ngoài cửa sổ 60 giây rồi đếm request còn lại: sliding window log, không phải token bucket. User được 10/phút; admin dùng limiter riêng 100/phút, không được miễn hoàn toàn. Vì RAM tách biệt giữa worker và mất khi restart, CP5 chuyển policy state sang Redis và dùng Lua để check/update nguyên tử.

### Exercise 4.4 — Cost guard

Ví dụ Part 4 đã có cost guard trong RAM: tính chi phí input/output token, chặn user với 402 khi hết ngân sách ngày và chặn toàn service với 503 khi hết ngân sách chung. Đây chưa phải quota tháng chia sẻ giữa các instance.

Thiết kế Redis cho $10/tháng: dùng bucket `cost:month:YYYY-MM` (hoặc thêm user ID nếu quota theo user), kiểm tra và giữ chỗ chi phí ước tính trước LLM bằng một Lua script nguyên tử; hết ngân sách trả 402. Sau LLM cộng chi phí thực và trả phần giữ chỗ thừa, lỗi LLM thì hoàn lại. Key hết hạn đầu tháng kế tiếp theo UTC; bucket tháng mới tự bắt đầu từ 0. Part 6 hiện thực cả ngân sách ngày và tháng với cách này.

Rate limit bảo vệ số lần gọi trong một cửa sổ thời gian; cost guard bảo vệ tổng tiền, vì request dài/model đắt có thể tiêu nhiều dù số lần gọi thấp. API key phù hợp giao tiếp service đơn giản; JWT hỗ trợ danh tính/role/hạn dùng; OAuth2 bổ sung luồng ủy quyền khi ứng dụng cần truy cập thay người dùng.

## Part 5 — Scaling & Reliability (CP4)

### Exercise 5.1–5.2 — Health và graceful shutdown

`/health` trả 200 khi process vẫn phục vụ được liveness; `/ready` trả 200 khi đủ dependency để nhận traffic, 503 khi startup/shutdown hoặc Redis mất kết nối. Không buộc `/health` thất bại theo Redis: restart hàng loạt agent không chữa được Redis, còn làm tăng tải khi phục hồi.

Chạy bản develop bằng `python app.py` để uvicorn quản lý signal sau khi module khởi tạo. Kết quả thật trong [evidence/cp4.json](evidence/cp4.json): `/health` 200, `/ready` 200, gửi SIGTERM lúc request chạy → request vẫn **200**, process exit **0**. Khi dùng uvicorn CLI, handler SIGTERM của ví dụ được đăng ký khi import có thể che handler server; lần thử đó không thoát trong timeout. Runner đã chuyển về entry point hướng dẫn. Không dùng pattern ghi đè signal này ở Part 6.

Graceful shutdown: đóng listener/ngừng nhận request mới, đợi request đang xử lý xong, chạy lifespan cleanup để đóng connection, sau đó thoát. SIGKILL không cho phép cleanup. Bản mẫu develop dùng lời gọi mock đồng bộ trong async endpoint nên có thể chặn event loop; Part 6 dùng sync endpoint để FastAPI đưa công việc vào thread pool.

### Exercise 5.3–5.5 — Redis và ba instance

```bash
cd 05-scaling-reliability/production
touch .env.local
docker compose -p k5-day14-scaling up -d --build --scale agent=3
python test_stateless.py
docker compose -p k5-day14-scaling down -v
```

Đã chạy đúng script gốc và lưu [evidence/cp4-stateless.txt](evidence/cp4-stateless.txt): **5 request** của cùng một session đi qua **3 instance**; đọc history có **10 message** (5 user + 5 assistant). Nginx phân phối tới các instance; mỗi instance đọc/ghi key session chung trong Redis nên không cần sticky session. Không sửa script và không tuyên bố script tự kill container: script gốc chỉ gửi request và đọc history.

Giới hạn của ví dụ: có fallback RAM khi Redis không sẵn sàng lúc khởi động, chưa an toàn để scale trong tình huống đó; update history là read-modify-write nên các request đồng thời cùng session có thể ghi đè. Thử nghiệm hiện tại là tuần tự, chứng minh chia sẻ state qua Redis giữa instance, chưa chứng minh xử lý conflict đồng thời. Part 6 không fallback RAM cho rate limit/budget. Stack CP4 đã dọn sau khi thu bằng chứng.

## Part 6 — Final Project (CP5)

Đã hoàn thiện các module trong `06-lab-complete/app/`, Dockerfile, Compose, ignore, env template và config Railway/Render. Không sửa script chấm hoặc golden dataset.

- Auth: header X-API-Key, so sánh constant-time, từ chối cả khi server chưa cấu hình key.
- Rate limit: Redis sorted set theo hash API key; Lua dùng Redis TIME để prune/count/add nguyên tử, UUID tránh trùng timestamp giữa worker; vượt giới hạn trả 429 và Retry-After.
- Budget: giữ chỗ chi phí input và tối đa 512 output token trong bucket UTC ngày/tháng bằng Lua; thiếu ngân sách trả 402 trước LLM. Ghi usage thật bằng transaction, hoàn tiền thừa/lỗi LLM. Bucket cũ được giữ thêm một ngày để request qua nửa đêm vẫn đối soát được.
- Redis mất kết nối: không fallback RAM, không crash lúc import; `/health` vẫn 200, `/ready` và `/ask` cần state trả 503.
- Logging: formatter `json.dumps`, có request ID, status và ms, không ghi câu hỏi/key/Redis URL chứa credential.
- Shutdown: uvicorn giữ signal handler; lifespan đóng Redis sau khi server đã drain request. Docker dùng `exec uvicorn` để server nhận SIGTERM, chạy user non-root và kiểm tra health theo PORT.

Kiểm tra đầy đủ bằng `python scripts/verify_final.py` trên Python 3.11.18 trong WSL2. Output script chấm nguyên bản: [evidence/cp5-production-ready.txt](evidence/cp5-production-ready.txt). Lần cuối **PASS 12/12, 43/43 checks**, image theo trường `.Size` mà checker dùng **63 MB**, Docker stop **1,4 giây**, exit 0.

```text
📋 Checklist Deliverable
   ✅ Dockerfile (multi-stage, < 500 MB)
   ✅ docker-compose.yml (agent + redis)
   ✅ .dockerignore
   ✅ Health check endpoint (GET /health)
   ✅ Readiness endpoint (GET /ready)
   ✅ API Key authentication
   ✅ Rate limiting
   ✅ Cost guard
   ✅ Config từ environment variables
   ✅ Structured logging
   ✅ Graceful shutdown
   ✅ Public URL ready (Railway / Render config)
Result: 12/12 tiêu chí đạt · 43/43 checks passed
🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Kiểm tra bổ sung trong [evidence/cp5-extra.json](evidence/cp5-extra.json): 5 input sai đều 422; thiếu/sai key đều 401; 20 request đồng thời qua hai worker cho đúng 10 response 200 và 10 response 429; dừng Redis thì health 200, ready 503, ask 503.

Mục `Public URL ready` của checker tại CP5 chỉ xác nhận config deploy. Kiểm tra URL cloud thực tế được ghi riêng tại Part 3/CP6; không suy ra từ kết quả script local. Giới hạn: chi phí của mock là ước lượng token, ngân sách toàn agent; reservation còn giữ tới hết bucket nếu process bị kill trước đối soát. Redis cloud miễn phí không đảm bảo bền dữ liệu qua restart datastore.

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

### CP2

- Codex build hai image, chạy container develop và Compose, đo bằng docker images/inspect, lưu HTTP response; sửa port Nginx sau lỗi bind thực tế trên Windows.
- Codex viết câu trả lời và lưu số đo thật; người học chưa tự sửa hay chạy lại. Không lấy kích thước mẫu trong README làm kết quả.

### CP3

- Codex đọc auth/rate limiter/cost guard, chạy API key và JWT flow thật; lưu raw curl 401/200/429 cùng dãy status, không lưu credential sinh trong phiên.
- Codex viết giải thích và thiết kế quota Redis; người học chưa tự sửa hoặc chạy lại. Runner có assertion đúng 10 lần 200 trước 429.

### CP4

- Codex chạy health/readiness và SIGTERM thật trên WSL, điều chỉnh entry point của runner theo code mẫu sau khi gặp timeout; chạy Compose ba replica và script stateless gốc, lưu output.
- Codex viết phân tích giới hạn của demo và dọn stack. Người học chưa tự sửa hoặc chạy lại; cần giải thích được vì sao history đủ qua các instance.

### CP5

- Codex viết code Part 6 từ khung theo hợp đồng K5: env/auth/Redis/Lua rate limit và budget/log/lifespan/Docker/Compose/deploy config.
- Codex chạy script chấm gốc đầy đủ, lưu output; kiểm tra thêm input sai, hai worker đồng thời và Redis outage. Đã giữ nguyên script chấm và golden dataset; không dùng số đo mẫu.
- Người học chưa tự sửa hay tự chạy lại. Cần đọc và giải thích được luồng Redis Lua, cách tính token mock/giữ chỗ ngân sách, lifecycle và các giới hạn ghi ở trên.

### Chuẩn bị CP6

- Codex đọc config Cloud Run, so sánh Railway/Render; tra tài liệu chính thức để chuẩn bị Blueprint và giới hạn Free, viết script kiểm tra bốn endpoint public.
- Đã tìm thấy tích hợp Render có thể hỗ trợ deploy nhưng chưa được người học cài/kết nối. Chưa có tài nguyên cloud, URL hay screenshot được xác nhận. Người học cần kết nối tài khoản để tiếp tục.

### CP6 — kiểm tra URL sau khi người học deploy thủ công

- Người học đã cấu hình Render trên dashboard, gửi ảnh Live và URL public. Theo yêu cầu người học, Codex merge cuonglk vào main và push merge commit 283bdca trước khi deploy.
- Codex gọi endpoint thật, lưu bằng chứng ba kiểm tra không cần key; bổ sung chế độ public-only và đọc file env riêng cho script để không yêu cầu gửi credential qua chat.
- Đã chuẩn bị file .env local bị gitignore, key còn trống. Chưa kiểm tra request có key; chưa thu đủ file screenshot trong repo. Người học cần điền key hiện tại vào file riêng và cung cấp ảnh đã che credential để tiếp tục hoàn tất CP6.

### CP6 — xác thực public hoàn tất

- Người học điền key vào .env riêng và xác nhận đã lưu. Codex chạy script đọc file này trong WSL2: health 200, ready 200, thiếu key 401, có key 200.
- Lưu report JSON không có key; kiểm tra Git chỉ thêm report và tài liệu, không thêm .env. Còn file ảnh minh chứng cloud trong repo; người học chưa tự chạy lại script.
