"""Reconcile CP8 report prose/tables with real Prometheus, Jaeger and CSV data."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / "evidence" / name).read_text(encoding="utf-8"))


def main():
    trace = read("cp8-trace-summary.json")
    timing = read("cp8-chaos-timing.json")
    metrics = read("cp8-metrics-scale3.json")["queries"]
    values = lambda key: metrics[key]["response"]["data"]["result"]
    scalar = lambda key: float(values(key)[0]["value"][1])
    logs = read("cp8-correlated-logs.json")
    slow_log = next(row for row in logs if row["trace_id"] == trace["slow_trace_id"] and row["event"] == "llm_call")
    error_log = next(row for row in logs if row["trace_id"] == trace["error_trace_id"] and row["event"] == "llm_error")
    total = trace["total_ms"]
    llm = trace["llm_span"]["ms"]
    lines = []
    for count in (1, 3):
        with (ROOT / f"benchmark-results/scale_{count}_stats.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        ask = next(row for row in rows if row["Name"] == "/ask")
        aggregate = next(row for row in rows if row["Name"] == "Aggregated")
        errors = int(ask["Failure Count"])
        requests = int(ask["Request Count"])
        lines.append(f"| {count} | {float(ask['Requests/s']):.2f} | {ask['50%']} | {ask['95%']} | {ask['99%']} | {errors}/{requests} ({errors/requests*100:.2f}%) |")
        assert int(aggregate["Request Count"]) >= requests
    instance_rates = ", ".join(f"`{row['metric']['instance']}`: {float(row['value'][1]):.2f} req/s" for row in values("rps_by_instance"))
    token_rates = ", ".join(f"{row['metric']['type']}: {float(row['value'][1]):.2f} token/s" for row in values("tokens_by_type"))
    section = f'''## 4. Observability stack (production)

Đã chạy đủ agent/Nginx/Prometheus/Grafana/Jaeger/Locust bằng project `k5-day14-observability`. Bộ unit test alert rules gốc PASS (`evidence/cp8-alert-rule-tests.txt`). Image public đã pull trực tiếp thành công trong lần thử lại, không cần đăng nhập; `evidence/cp8-startup.txt` giữ lỗi 429 của lần trước để ghi nhận sự cố, không phải trạng thái cuối.

Hai sửa chữa khi chạy thực tế: Dockerfile benchmark production chuyển dependency từ user site-packages sang `/opt/venv` vì user runtime không tìm thấy uvicorn; Locust headless dùng `run --no-deps` để Compose không tự đưa agent về `deploy.replicas: 2`. CSV của lần thử bị đổi replica được giữ ở `evidence/cp8-initial-attempt/` và **không dùng** trong bảng kết quả. Các lượt chính được xác minh có đúng 1 và 3 healthy target qua API Prometheus (`cp8-targets-1.json`, `cp8-targets-3.json`).

### 4.1 Screenshot và Exercise 7.4

- [x] [Grafana có tải, ba instance](screenshots/grafana-dashboard.png).
- [x] [Trace chậm, chọn span LLM](screenshots/jaeger-slow-trace.png).
- [x] [Trace lỗi có event exception](screenshots/jaeger-error-trace.png).
- [x] [Prometheus có hai alert cùng firing](screenshots/prometheus-alert-firing.png).

Ảnh Grafana hiển thị cửa sổ đo thực tế của lượt 3 instance (16:36:33–16:38:23 GMT+7). Snapshot cuối lượt lưu tại `evidence/cp8-metrics-scale3.json`; query và timestamp cũng nằm trong file, có thể đối chiếu mọi giá trị dưới đây.

1. p95 từ histogram Prometheus là **{scalar('p95_seconds')*1000:.2f} ms**, average **{scalar('avg_seconds')*1000:.2f} ms**. p95 cao hơn mean cho thấy phần đuôi chậm, nhưng cần xem cả p99 để thấy nhóm slow rate 3%. Histogram nội suy theo bucket, không bằng percentile trực tiếp của Locust; không so chúng như cùng một phép đo.
2. Requests/s theo instance: {instance_rates}. Ba mức gần nhau, phù hợp Nginx chia traffic; đây là snapshot rate một phút, không khẳng định chia đều tuyệt đối từng request.
3. Token rate: {token_rates}. Input gồm system prompt + context retrieval + câu hỏi, trong khi output là câu trả lời ngắn. Panel token của dashboard vẽ stacked area; vị trí đỉnh của đường output là giá trị cộng dồn, không phải output token rate riêng.
4. `GET http://localhost:8080/metrics` trả **404** do Nginx chặn đường vận hành này. Prometheus scrape trực tiếp agent trong network nội bộ, nên vẫn có metric. HTTP output thật tại `evidence/cp8-public-metrics.txt`.

### 4.2 Thí nghiệm lỗi và tail latency

Locust giữ 30 users, spawn rate 5. Thời gian dưới đây đo từ lúc bắt đầu lệnh áp dụng cấu hình (gồm thời gian recreate và chờ scrape), poll API mỗi 5 giây; đây là lần đầu quan sát firing, có sai số lấy mẫu khoảng 5 giây. Giữ nguyên biểu thức và `for` của alert rules gốc.

| Thí nghiệm | Thay đổi | Alert firing | Thời gian quan sát | Panel |
|---|---|---|---:|---|
| A | Error rate 0.01 → 0.2, giữ slow rate 0.03 | AgentHighErrorRate | {timing['first_firing_elapsed_s']['AgentHighErrorRate']:.2f} giây | Error rate, HTTP status 503 |
| B | Sau A, tăng slow rate 0.03 → 0.3, giữ error rate 0.2 | AgentHighLatencyP95 | {timing['latency_firing_after_phase_b_s']:.2f} giây từ lúc áp dụng B | p95/p99 latency |

B bắt đầu tại t={timing['phase_b_started_elapsed_s']:.2f}s của toàn thí nghiệm; hai alert cùng firing lần đầu quan sát ở t={timing['first_firing_elapsed_s']['AgentHighLatencyP95']:.2f}s. File `evidence/cp8-chaos-timing.json` lưu toàn bộ lần poll và `cp8-alerts-firing.json` lưu hai alert cùng firing. A và B được thực hiện nối tiếp, B giữ A để chụp cả hai alert; vì vậy B không phải thí nghiệm cô lập hoàn toàn. CSV chaos chứa cả giai đoạn recreate/DNS, không dùng làm benchmark scale chuẩn.

Thí nghiệm C/D/E không chạy; không ghi thời gian firing giả. Nhận xét E từ thiết kế: đổi v2 → v1 vẫn có thể trả HTTP 200 nhanh và ít lỗi, trong khi nội dung sai. Cần golden-dataset eval/quality gate, đánh giá mẫu traffic và feedback để phát hiện; health/latency/error HTTP không đủ. Với D, pause giữ target trong DNS và làm scrape thất bại; stop có thể khiến target biến mất. Lỗi 504 ở Nginx không nhất thiết xuất hiện trong counter của agent, nên cần thêm metric ở ingress hoặc synthetic check từ bên ngoài.

### 4.3 Debug bằng trace và log

Chọn trace chậm nhất trong **mẫu {trace['sample_traces']} trace** trả bởi query đã lưu (không tuyên bố chậm nhất trong mọi trace của toàn bộ lần chạy):

- Trace ID: `{trace['slow_trace_id']}`.
- Tổng duration: **{total:.3f} ms**.
- Span công việc chiếm thời gian chính: **`{trace['llm_span']['name']}` — {llm:.3f} ms ({llm/total*100:.2f}%)**.
- Root `POST /ask` bao toàn bộ pipeline nên duration lớn nhất về mặt hình thức; LLM child span là nơi gây chậm. Retrieval chỉ chiếm phần nhỏ còn lại.
- Error trace ID: `{trace['error_trace_id']}`, có status ERROR và event `exception` ở LLM span. JSON thô theo API v3/OTLP được lưu trong `cp8-slow-trace.json` và `cp8-error-trace.json`; `cp8-correlated-logs.json` chứa log của đúng hai ID.

Dòng log khớp trace chậm:

```json
{json.dumps(slow_log, ensure_ascii=False)}
```

Dòng log khớp trace lỗi:

```json
{json.dumps(error_log, ensure_ascii=False)}
```

Jaeger trong repo dùng API v3, endpoint cũ `/api/traces` không còn dùng được trong lần chạy này. Script thu bằng `/api/v3/traces`, theo [query service IDL chính thức](https://github.com/jaegertracing/jaeger-idl/blob/main/proto/api_v3/query_service.proto), rồi chuẩn hóa tên span và nanosecond để tính duration; không thay đổi dữ liệu gốc trong trường `otlp`.

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Bảng dùng riêng dòng **POST /ask** trong mỗi CSV, tránh trộn `/health` vốn rất nhanh. Mỗi lượt chạy `-u 100 -r 10 -t 2m`, cùng mock small/error rate 0.01/slow rate 0.03; không load test service cloud.

| Instance | RPS /ask | p50 (ms) | p95 (ms) | p99 (ms) | Failures / requests |
|---|---|---|---|---|---|
{chr(10).join(lines)}

Nguồn: `benchmark-results/scale_1_stats.csv`, `scale_3_stats.csv`; bản gốc giữ trong thư mục production, có failures/exceptions/history CSV và CLI output riêng tại evidence. Locust exit 1 do lỗi upstream mô phỏng, không phải mất báo cáo; bảng dùng nguyên số đo của lượt chuẩn.

Scale không cải thiện throughput hay latency đáng kể ở mức 100 users này. Locust có think time 0.5–2 giây nên mô hình closed-loop và số user giới hạn RPS; một agent async chưa bị ép đến giới hạn. Thời gian xử lý chủ yếu là mock LLM sleep và retrieval, tăng replica không rút ngắn latency provider mô phỏng. p99 vẫn quanh 1.7 giây do slow rate, còn chênh lệch p95 230 → 220 ms có thể do jitter/lấy mẫu; không suy ra scale ba lần sẽ nhanh ba lần.

## 6. Kết luận

1. Average che tail latency; percentile và error rate phải xem riêng, và histogram có sai số bucket.
2. Cost/câu đúng thể hiện lợi ích retrieval dù token/câu và latency tăng; quality gate phát hiện regression mà metric HTTP không thấy.
3. Metrics cho biết hệ thống đang bất thường ở đâu; trace chỉ ra LLM span gây chậm, log có trace_id cung cấp ngữ cảnh của cùng request. Kiểm tra target count và dependency behavior là điều kiện để phép đo scale có ý nghĩa.

Nếu vận hành thật, bổ sung queue depth, timeout/retry ở provider, Redis health, 429/402 theo quota, cache hit rate, metric ingress/synthetic availability, cost/tenant và chất lượng câu trả lời theo dataset/feedback. Chọn alert window theo mức ảnh hưởng: for=0 dễ báo động do spike, for=30m có thể phát hiện quá muộn.

Đã thu bằng chứng trước khi dọn stack. Bảy ảnh là screenshot của màn hình/trang service thật; hai ảnh Render và hai ảnh span chi tiết có bản capture gốc JPEG trong evidence, chỉ đổi định dạng PNG khi đóng gói. Không dùng ảnh AI hay ảnh dựng thay kết quả.
'''
    path = ROOT / "BENCHMARK_REPORT.md"
    text = path.read_text(encoding="utf-8")
    prefix = text.split("## 4. Observability stack (production)", 1)[0]
    prefix = prefix.replace("> CP7 đã hoàn thành. CP8 chưa có số đo do Docker Hub trả HTTP 429 khi tải image; các ô CP8 để trống có chủ đích, không phải số 0.",
                            "> CP7 và CP8 đã hoàn thành bằng số đo và ảnh service thật; sự cố Docker Hub 429 ở lần trước đã hết khi pull trực tiếp lại.")
    path.write_text(prefix + section, encoding="utf-8")


if __name__ == "__main__":
    main()
