"""Fill the CP7 template tables directly from the submitted JSON reports."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report(name):
    return json.loads((ROOT / "reports" / f"{name}.json").read_text(encoding="utf-8"))


def main():
    target = ROOT / "BENCHMARK_REPORT.md"
    text = target.read_text(encoding="utf-8")
    text = text.replace("> Copy file này thành `BENCHMARK_REPORT.md` trong repo của bạn và điền đầy đủ.\n> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.",
                        "> CP7 đã hoàn thành. CP8 chưa có số đo do Docker Hub trả HTTP 429 khi tải image; các ô CP8 để trống có chủ đích, không phải số 0.\n> Số liệu CP7 lấy trực tiếp từ JSON trong reports/; lệnh và exit code ở evidence/cp7-commands.json, output ở evidence/cp7-cli.txt.")
    text = text.replace("**Họ tên:** ...", "**Họ tên:** Lê Khánh Cường")
    text = text.replace("**Ngày chạy:** ...", "**Ngày chạy:** 26/11/2026 (GMT+7)")
    text = text.replace("**Môi trường:** (vd MacBook M2, Docker Desktop 4 CPU / 8GB RAM)",
                        "**Môi trường:** Windows + Ubuntu WSL2 x86_64, Python 3.11.18; kernel 6.6.87.2. Docker Engine 29.1.5 báo 16 CPU, 7.958.884.352 byte RAM (khoảng 7,41 GiB). Agent develop chạy trực tiếp trong WSL2, một process mỗi phiên bản. Model mock-llm-small; latency/jitter/retrieval dùng mặc định. Load test bật MOCK_ERROR_RATE=0.01; eval dùng 0 để cô lập chất lượng khỏi lỗi upstream ngẫu nhiên.")
    text = text.replace("| p95 latency `/ask` | < ___ ms | |", "| p95 latency `/ask` | ≤ 500 ms | Bảo vệ trải nghiệm của 95% request; ngưỡng CLI mặc định |")
    text = text.replace("| Error rate `/ask` | < ___ % | |", "| Error rate `/ask` | ≤ 2% | Giới hạn lỗi upstream trong load test |")
    text = text.replace("| Accuracy trên golden dataset | ≥ ___ % | |", "| Accuracy trên golden dataset | 100%, không regression sau sửa | Mục tiêu CP7 là 23/23; gate mặc định eval ban đầu là 80% |")
    for c in (1, 10, 50, 100):
        r = report(f"load_v2_c{c}")
        lat = r["latency_ms"]
        text = text.replace(f"| {c} | | | | | | |", f"| {c} | {r['rps']} | {lat['p50']} | {lat['p95']} | {lat['p99']} | {r['error_rate']*100:.2f}% | {'PASS' if r['slo']['passed'] else 'FAIL'} |")
    for label, rate in (("0", "0"), ("0.03 (mặc định)", "0.03"), ("0.1", "0.1")):
        r = report(f"load_v2_slow_{rate}")
        lat = r["latency_ms"]
        text = text.replace(f"| {label} | | | |", f"| {label} | {lat['avg']} | {lat['p95']} | {lat['p99']} |")
    versions = [report(name) for name in ("eval_v1", "eval_v2", "eval_v2_fixed")]
    for label, field in (("Accuracy", "accuracy"), ("Avg tokens / câu", "avg_tokens"),
                         ("Tổng cost (USD)", "total_cost_usd"), ("Cost / câu đúng (USD)", "cost_per_correct_usd")):
        values = [f"{r['accuracy']*100:.2f}% ({r['passed']}/{r['total']})" if field == "accuracy" else str(r[field]) for r in versions]
        text = text.replace(f"| {label} | | | |", f"| {label} | {' | '.join(values)} |")
    text = text.replace("| Quality gate | PASS / FAIL | PASS / FAIL | PASS / FAIL |",
                        "| Quality gate | FAIL (exit 1, ngưỡng 80%) | PASS (exit 0, ngưỡng 80%) | PASS (exit 0, ngưỡng 100%, 0 regression) |")
    text = text.replace("| | | |", "| security-02 | token, hết hạn, chữ ký | Thêm tài liệu phân biệt JWT với API key, kiểm chữ ký và hạn dùng |\n| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu HPA theo CPU/memory và custom metrics |", 1)
    text = text.replace("**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?\n\n...",
                        "**Nhận xét:** RPS tăng từ 4,04 lên 143,53 khi concurrency tăng từ 1 lên 100, không tuyến tính 100 lần. Latency p95 tăng từ 218 lên 364,7 ms khi client/server cạnh tranh tài nguyên và xử lý đồng thời. Cả bốn lượt 300 request đều đạt SLO p95 và error rate. Một phần thời gian chạy ở concurrency cao dùng để chờ các request đuôi chậm cuối cùng; 300 request là phép đo ngắn, chưa phải kiểm chứng tải bền vững.")
    text = text.replace("**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?\n\n...",
                        "**Nhận xét:** Slow rate 0 → 0,03 làm p99 tăng 226 → 1703,7 ms, trong khi avg chỉ tăng 190 → 218,5 ms và p95 gần như không đổi. Khi slow rate 0,1, hơn 5% request thành công rơi vào đuôi chậm nên p95 lên 1685,3 ms dù avg mới 336 ms: latency SLO FAIL, error rate vẫn 1%. p99 nhạy với đuôi ít gặp hơn p95; average che trải nghiệm nhóm người dùng bị chậm. Percentile của CLI chỉ tính request status 200; error rate tính trên toàn bộ request. Mỗi lượt có 300 request, concurrency 20, warm-up không được tính; các lượt độc lập có jitter ngẫu nhiên, không khẳng định đây là quan hệ nhân quả chính xác đến từng ms.")
    text = text.replace("**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**\n\n...",
                        "**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:** v2 thêm retrieval và context nên tokens/câu tăng 57,2 → 108,7 → 115,6, p95 eval tăng 188,8 → 209 → 210,9 ms. Tổng cost tăng nhưng cost/câu đúng giảm từ 0,00040515 xuống 0,00003511 USD (khoảng 11,54 lần rẻ hơn). Cost/câu đúng đánh giá cả lượng chi phí bị lãng phí vào câu sai; token và giá là mô phỏng, không phải hóa đơn provider thật. total_cost được CLI làm tròn 6 chữ số, cost/câu đúng làm tròn 8 chữ số nên lấy tổng đã làm tròn chia số câu đúng có thể lệch nhỏ.\n\n**Quality gate:** chạy v1 với baseline v2 phát hiện 20 regression và exit code 1, lưu reports/eval_v1_regression.json. Workflow `.github/workflows/quality-gate.yml` khởi động v2 với lỗi ngẫu nhiên tắt, đợi health có timeout, chạy eval với `--min-accuracy 1.0 --baseline ../../../reports/eval_v2_fixed.json`. Bất kỳ câu sai/regression làm job fail. Đã chạy tương đương lệnh eval ở local; chưa xác nhận GitHub Actions đã thực thi. Để chặn merge bắt buộc, repository owner cần đặt job eval thành required status check trong branch protection/ruleset.")
    text = text.replace("- [ ] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**", "- [ ] Trang Alerts của Prometheus với ít nhất **2 alert cùng firing**, theo yêu cầu K5")
    text = text.replace("### 4.1 Screenshot", "CP8 đang bị chặn khi pull `locustio/locust:2.47.0`: Docker Hub trả HTTP 429 Too Many Requests. Chưa chạy Locust production, chưa có dashboard/trace/alert hoặc CSV scaling; không điền số ước lượng.\n\n### 4.1 Screenshot")
    text = text.replace("**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**\n\n...",
                        "**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?** Hạ tầng có thể vẫn nhanh và ít lỗi HTTP khi nội dung trả lời sai. Dùng offline eval/quality gate trên golden dataset, đánh giá mẫu traffic thật, theo dõi feedback và quality metrics. Đây là phân tích từ code; chưa chạy thí nghiệm E trên stack production.")
    text = text.replace("  1. ...\n  2. ...\n  3. ...", "  1. Average che tail latency; percentile và error rate cần được xem riêng.\n  2. Cost/câu đúng cho thấy lợi ích của retrieval dù tổng token và latency tăng.\n  3. Quality gate bắt regression mà healthcheck và metrics HTTP không thể phản ánh.")
    target.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
