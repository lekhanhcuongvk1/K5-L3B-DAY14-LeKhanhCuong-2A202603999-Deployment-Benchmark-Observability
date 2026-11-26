# Benchmark & Observability Report — Day 14

> CP7 và CP8 đã hoàn thành bằng số đo và ảnh service thật; sự cố Docker Hub 429 ở lần trước đã hết khi pull trực tiếp lại.
> Số liệu CP7 lấy trực tiếp từ JSON trong reports/; lệnh và exit code ở evidence/cp7-commands.json, output ở evidence/cp7-cli.txt.

**Họ tên:** Lê Khánh Cường
**Ngày chạy:** 26/11/2026 (GMT+7)
**Môi trường:** Windows + Ubuntu WSL2 x86_64, Python 3.11.18; kernel 6.6.87.2. Docker Engine 29.1.5 báo 16 CPU, 7.958.884.352 byte RAM (khoảng 7,41 GiB). Agent develop chạy trực tiếp trong WSL2, một process mỗi phiên bản. Model mock-llm-small; latency/jitter/retrieval dùng mặc định. Load test bật MOCK_ERROR_RATE=0.01; eval dùng 0 để cô lập chất lượng khỏi lỗi upstream ngẫu nhiên.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Bảo vệ trải nghiệm của 95% request; ngưỡng CLI mặc định |
| Error rate `/ask` | ≤ 2% | Giới hạn lỗi upstream trong load test |
| Accuracy trên golden dataset | 100%, không regression sau sửa | Mục tiêu CP7 là 23/23; gate mặc định eval ban đầu là 80% |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.04 | 189.3 | 218.0 | 1712.0 | 1.33% | PASS |
| 10 | 38.95 | 188.8 | 220.7 | 1693.2 | 0.67% | PASS |
| 50 | 108.58 | 196.4 | 256.6 | 1710.7 | 1.00% | PASS |
| 100 | 143.53 | 206.4 | 364.7 | 1706.2 | 1.67% | PASS |

**Nhận xét:** RPS tăng từ 4,04 lên 143,53 khi concurrency tăng từ 1 lên 100, không tuyến tính 100 lần. Latency p95 tăng từ 218 lên 364,7 ms khi client/server cạnh tranh tài nguyên và xử lý đồng thời. Cả bốn lượt 300 request đều đạt SLO p95 và error rate. Một phần thời gian chạy ở concurrency cao dùng để chờ các request đuôi chậm cuối cùng; 300 request là phép đo ngắn, chưa phải kiểm chứng tải bền vững.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 190.0 | 219.3 | 226.0 |
| 0.03 (mặc định) | 218.5 | 217.3 | 1703.7 |
| 0.1 | 336.0 | 1685.3 | 1707.2 |

**Nhận xét:** Slow rate 0 → 0,03 làm p99 tăng 226 → 1703,7 ms, trong khi avg chỉ tăng 190 → 218,5 ms và p95 gần như không đổi. Khi slow rate 0,1, hơn 5% request thành công rơi vào đuôi chậm nên p95 lên 1685,3 ms dù avg mới 336 ms: latency SLO FAIL, error rate vẫn 1%. p99 nhạy với đuôi ít gặp hơn p95; average che trải nghiệm nhóm người dùng bị chậm. Percentile của CLI chỉ tính request status 200; error rate tính trên toàn bộ request. Mỗi lượt có 300 request, concurrency 20, warm-up không được tính; các lượt độc lập có jitter ngẫu nhiên, không khẳng định đây là quan hệ nhân quả chính xác đến từng ms.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | 100.00% (23/23) |
| Avg tokens / câu | 57.2 | 108.7 | 115.6 |
| Tổng cost (USD) | 0.000405 | 0.000756 | 0.000807 |
| Cost / câu đúng (USD) | 0.00040515 | 3.599e-05 | 3.511e-05 |
| Quality gate | FAIL (exit 1, ngưỡng 80%) | PASS (exit 0, ngưỡng 80%) | PASS (exit 0, ngưỡng 100%, 0 regression) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu phân biệt JWT với API key, kiểm chữ ký và hạn dùng |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu HPA theo CPU/memory và custom metrics |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:** v2 thêm retrieval và context nên tokens/câu tăng 57,2 → 108,7 → 115,6, p95 eval tăng 188,8 → 209 → 210,9 ms. Tổng cost tăng nhưng cost/câu đúng giảm từ 0,00040515 xuống 0,00003511 USD (khoảng 11,54 lần rẻ hơn). Cost/câu đúng đánh giá cả lượng chi phí bị lãng phí vào câu sai; token và giá là mô phỏng, không phải hóa đơn provider thật. total_cost được CLI làm tròn 6 chữ số, cost/câu đúng làm tròn 8 chữ số nên lấy tổng đã làm tròn chia số câu đúng có thể lệch nhỏ.

**Quality gate:** chạy v1 với baseline v2 phát hiện 20 regression và exit code 1, lưu reports/eval_v1_regression.json. Workflow `.github/workflows/quality-gate.yml` khởi động v2 với lỗi ngẫu nhiên tắt, đợi health có timeout, chạy eval với `--min-accuracy 1.0 --baseline ../../../reports/eval_v2_fixed.json`. Bất kỳ câu sai/regression làm job fail. Đã chạy tương đương lệnh eval ở local; chưa xác nhận GitHub Actions đã thực thi. Để chặn merge bắt buộc, repository owner cần đặt job eval thành required status check trong branch protection/ruleset.

---

## 4. Observability stack (production)

Đã chạy đủ agent/Nginx/Prometheus/Grafana/Jaeger/Locust bằng project `k5-day14-observability`. Bộ unit test alert rules gốc PASS (`evidence/cp8-alert-rule-tests.txt`). Image public đã pull trực tiếp thành công trong lần thử lại, không cần đăng nhập; `evidence/cp8-startup.txt` giữ lỗi 429 của lần trước để ghi nhận sự cố, không phải trạng thái cuối.

Hai sửa chữa khi chạy thực tế: Dockerfile benchmark production chuyển dependency từ user site-packages sang `/opt/venv` vì user runtime không tìm thấy uvicorn; Locust headless dùng `run --no-deps` để Compose không tự đưa agent về `deploy.replicas: 2`. CSV của lần thử bị đổi replica được giữ ở `evidence/cp8-initial-attempt/` và **không dùng** trong bảng kết quả. Các lượt chính được xác minh có đúng 1 và 3 healthy target qua API Prometheus (`cp8-targets-1.json`, `cp8-targets-3.json`).

### 4.1 Screenshot và Exercise 7.4

- [x] [Grafana có tải, ba instance](screenshots/grafana-dashboard.png).
- [x] [Trace chậm, chọn span LLM](screenshots/jaeger-slow-trace.png).
- [x] [Trace lỗi có event exception](screenshots/jaeger-error-trace.png).
- [x] [Prometheus có hai alert cùng firing](screenshots/prometheus-alert-firing.png).

Ảnh Grafana hiển thị cửa sổ đo thực tế của lượt 3 instance (16:36:33–16:38:23 GMT+7). Snapshot cuối lượt lưu tại `evidence/cp8-metrics-scale3.json`; query và timestamp cũng nằm trong file, có thể đối chiếu mọi giá trị dưới đây.

1. p95 từ histogram Prometheus là **293.67 ms**, average **234.68 ms**. p95 cao hơn mean cho thấy phần đuôi chậm, nhưng cần xem cả p99 để thấy nhóm slow rate 3%. Histogram nội suy theo bucket, không bằng percentile trực tiếp của Locust; không so chúng như cùng một phép đo.
2. Requests/s theo instance: `172.24.0.8:8000`: 20.31 req/s, `172.24.0.4:8000`: 20.86 req/s, `172.24.0.9:8000`: 20.60 req/s. Ba mức gần nhau, phù hợp Nginx chia traffic; đây là snapshot rate một phút, không khẳng định chia đều tuyệt đối từng request.
3. Token rate: input: 4780.46 token/s, output: 2517.56 token/s. Input gồm system prompt + context retrieval + câu hỏi, trong khi output là câu trả lời ngắn. Panel token của dashboard vẽ stacked area; vị trí đỉnh của đường output là giá trị cộng dồn, không phải output token rate riêng.
4. `GET http://localhost:8080/metrics` trả **404** do Nginx chặn đường vận hành này. Prometheus scrape trực tiếp agent trong network nội bộ, nên vẫn có metric. HTTP output thật tại `evidence/cp8-public-metrics.txt`.

### 4.2 Thí nghiệm lỗi và tail latency

Locust giữ 30 users, spawn rate 5. Thời gian dưới đây đo từ lúc bắt đầu lệnh áp dụng cấu hình (gồm thời gian recreate và chờ scrape), poll API mỗi 5 giây; đây là lần đầu quan sát firing, có sai số lấy mẫu khoảng 5 giây. Giữ nguyên biểu thức và `for` của alert rules gốc.

| Thí nghiệm | Thay đổi | Alert firing | Thời gian quan sát | Panel |
|---|---|---|---:|---|
| A | Error rate 0.01 → 0.2, giữ slow rate 0.03 | AgentHighErrorRate | 82.52 giây | Error rate, HTTP status 503 |
| B | Sau A, tăng slow rate 0.03 → 0.3, giữ error rate 0.2 | AgentHighLatencyP95 | 147.67 giây từ lúc áp dụng B | p95/p99 latency |

B bắt đầu tại t=82.55s của toàn thí nghiệm; hai alert cùng firing lần đầu quan sát ở t=230.19s. File `evidence/cp8-chaos-timing.json` lưu toàn bộ lần poll và `cp8-alerts-firing.json` lưu hai alert cùng firing. A và B được thực hiện nối tiếp, B giữ A để chụp cả hai alert; vì vậy B không phải thí nghiệm cô lập hoàn toàn. CSV chaos chứa cả giai đoạn recreate/DNS, không dùng làm benchmark scale chuẩn.

Thí nghiệm C/D/E không chạy; không ghi thời gian firing giả. Nhận xét E từ thiết kế: đổi v2 → v1 vẫn có thể trả HTTP 200 nhanh và ít lỗi, trong khi nội dung sai. Cần golden-dataset eval/quality gate, đánh giá mẫu traffic và feedback để phát hiện; health/latency/error HTTP không đủ. Với D, pause giữ target trong DNS và làm scrape thất bại; stop có thể khiến target biến mất. Lỗi 504 ở Nginx không nhất thiết xuất hiện trong counter của agent, nên cần thêm metric ở ingress hoặc synthetic check từ bên ngoài.

### 4.3 Debug bằng trace và log

Chọn trace chậm nhất trong **mẫu 200 trace** trả bởi query đã lưu (không tuyên bố chậm nhất trong mọi trace của toàn bộ lần chạy):

- Trace ID: `e5e78f66e2a1f1ce5a68d8cc6cf8d0fe`.
- Tổng duration: **1704.737 ms**.
- Span công việc chiếm thời gian chính: **`chat mock-llm-small` — 1685.300 ms (98.86%)**.
- Root `POST /ask` bao toàn bộ pipeline nên duration lớn nhất về mặt hình thức; LLM child span là nơi gây chậm. Retrieval chỉ chiếm phần nhỏ còn lại.
- Error trace ID: `4ee07b02137f8e724af3491cfa7c150f`, có status ERROR và event `exception` ở LLM span. JSON thô theo API v3/OTLP được lưu trong `cp8-slow-trace.json` và `cp8-error-trace.json`; `cp8-correlated-logs.json` chứa log của đúng hai ID.

Dòng log khớp trace chậm:

```json
{"ts": "2026-11-26T09:38:19.963626+00:00", "level": "INFO", "service": "observable-agent", "instance": "3a14862687ff", "event": "llm_call", "trace_id": "e5e78f66e2a1f1ce5a68d8cc6cf8d0fe", "span_id": "247601ab68170521", "request_id": "969e00e384d2", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 95, "output_tokens": 55, "cost_usd": 4.7e-05, "llm_ms": 1684.9}
```

Dòng log khớp trace lỗi:

```json
{"ts": "2026-11-26T09:38:21.950145+00:00", "level": "INFO", "service": "observable-agent", "instance": "3a14862687ff", "event": "llm_error", "trace_id": "4ee07b02137f8e724af3491cfa7c150f", "span_id": "eb3bea5bb4e4da2b", "request_id": "f43198d25240", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

Jaeger trong repo dùng API v3, endpoint cũ `/api/traces` không còn dùng được trong lần chạy này. Script thu bằng `/api/v3/traces`, theo [query service IDL chính thức](https://github.com/jaegertracing/jaeger-idl/blob/main/proto/api_v3/query_service.proto), rồi chuẩn hóa tên span và nanosecond để tính duration; không thay đổi dữ liệu gốc trong trường `otlp`.

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Bảng dùng riêng dòng **POST /ask** trong mỗi CSV, tránh trộn `/health` vốn rất nhanh. Mỗi lượt chạy `-u 100 -r 10 -t 2m`, cùng mock small/error rate 0.01/slow rate 0.03; không load test service cloud.

| Instance | RPS /ask | p50 (ms) | p95 (ms) | p99 (ms) | Failures / requests |
|---|---|---|---|---|---|
| 1 | 59.81 | 190 | 230 | 1700 | 72/7141 (1.01%) |
| 3 | 60.08 | 190 | 220 | 1700 | 74/7174 (1.03%) |

Nguồn: `benchmark-results/scale_1_stats.csv`, `scale_3_stats.csv`; bản gốc giữ trong thư mục production, có failures/exceptions/history CSV và CLI output riêng tại evidence. Locust exit 1 do lỗi upstream mô phỏng, không phải mất báo cáo; bảng dùng nguyên số đo của lượt chuẩn.

Scale không cải thiện throughput hay latency đáng kể ở mức 100 users này. Locust có think time 0.5–2 giây nên mô hình closed-loop và số user giới hạn RPS; một agent async chưa bị ép đến giới hạn. Thời gian xử lý chủ yếu là mock LLM sleep và retrieval, tăng replica không rút ngắn latency provider mô phỏng. p99 vẫn quanh 1.7 giây do slow rate, còn chênh lệch p95 230 → 220 ms có thể do jitter/lấy mẫu; không suy ra scale ba lần sẽ nhanh ba lần.

## 6. Kết luận

1. Average che tail latency; percentile và error rate phải xem riêng, và histogram có sai số bucket.
2. Cost/câu đúng thể hiện lợi ích retrieval dù token/câu và latency tăng; quality gate phát hiện regression mà metric HTTP không thấy.
3. Metrics cho biết hệ thống đang bất thường ở đâu; trace chỉ ra LLM span gây chậm, log có trace_id cung cấp ngữ cảnh của cùng request. Kiểm tra target count và dependency behavior là điều kiện để phép đo scale có ý nghĩa.

Nếu vận hành thật, bổ sung queue depth, timeout/retry ở provider, Redis health, 429/402 theo quota, cache hit rate, metric ingress/synthetic availability, cost/tenant và chất lượng câu trả lời theo dataset/feedback. Chọn alert window theo mức ảnh hưởng: for=0 dễ báo động do spike, for=30m có thể phát hiện quá muộn.

Đã thu bằng chứng trước khi dọn stack. Bảy ảnh là screenshot của màn hình/trang service thật; hai ảnh Render và hai ảnh span chi tiết có bản capture gốc JPEG trong evidence, chỉ đổi định dạng PNG khi đóng gói. Không dùng ảnh AI hay ảnh dựng thay kết quả.
