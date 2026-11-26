# Benchmark & Observability Report — Day 14

> CP7 đã hoàn thành. CP8 chưa có số đo do Docker Hub trả HTTP 429 khi tải image; các ô CP8 để trống có chủ đích, không phải số 0.
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

CP8 đang bị chặn khi pull `locustio/locust:2.47.0` hoặc `nginx:1.28-alpine`: Docker Hub trả HTTP 429 Too Many Requests (lần thử cuối lưu ở `evidence/cp8-startup.txt`). Chưa chạy Locust production, chưa có dashboard/trace/alert hoặc CSV scaling; không điền số ước lượng.

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất **2 alert cùng firing**, theo yêu cầu K5

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?** Hạ tầng có thể vẫn nhanh và ít lỗi HTTP khi nội dung trả lời sai. Dùng offline eval/quality gate trên golden dataset, đánh giá mẫu traffic thật, theo dõi feedback và quality metrics. Đây là phân tích từ code; chưa chạy thí nghiệm E trên stack production.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

...

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. Average che tail latency; percentile và error rate cần được xem riêng.
  2. Cost/câu đúng cho thấy lợi ích của retrieval dù tổng token và latency tăng.
  3. Quality gate bắt regression mà healthcheck và metrics HTTP không thể phản ánh.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

...
