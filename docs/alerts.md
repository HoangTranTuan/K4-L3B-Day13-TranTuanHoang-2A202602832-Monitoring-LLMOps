# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Latency P95 của `response_sent.latency_ms` (ngưỡng $\le 3000$ ms)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000` duy trì trong 5 phút liên tục
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn để nhận câu trả lời, trải nghiệm tương tác chat bị suy giảm hoặc timeout.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Mở panel `Latency` trên dashboard để xác nhận xem P95/P99 bắt đầu tăng vọt từ thời điểm nào, TTFT (Time to First Token) có tăng tương ứng hay chỉ tăng ở tổng thời gian hoàn thành.
  2. **Logs:** Lọc file log `data/logs.jsonl` trong khoảng thời gian bị chậm, tìm các dòng log có `event == "response_sent"` và `latency_ms > 3000`. Trích xuất một `correlation_id` đại diện.
  3. **Traces:** Mở trace có `correlation_id` đó trên Langfuse, so sánh waterfall thời gian thực thi của span `retrieval` và span `generation` để xác định chính xác nút thắt cổ chai nằm ở RAG hay LLM.
- Mitigation tạm thời:
  - Nếu span `retrieval` bị chậm do vector store (kịch bản `rag_slow`): tắt incident bằng lệnh `python scripts/inject_incident.py --scenario rag_slow --disable` hoặc restart caching layer.
  - Nếu span `generation` bị chậm do prompt mới hoặc model quá tải: rollback label `production` về prompt version ổn định trước đó trên Langfuse.
- Owner: `student-2A202602832`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỉ lệ lỗi tổng thể trên hệ thống (`error_rate_pct_max: 2%`)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` duy trì trong 3 phút liên tục
- Ảnh hưởng tới người dùng: Người dùng nhận mã phản hồi lỗi HTTP 500 hoặc thông báo lỗi hệ thống, không nhận được câu trả lời từ trợ lý AI.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Kiểm tra panel `Errors` trên dashboard để đánh giá tỉ lệ lỗi tổng và xem breakdown phân bố số lượng lỗi theo từng loại `error_type`.
  2. **Logs:** Lọc các log có `event == "request_failed"` hoặc `level == "error"` trong `data/logs.jsonl`, đọc trường `payload.detail` và `error_type` (ví dụ `RuntimeError: Vector store timeout`).
  3. **Traces:** Tra cứu `correlation_id` của request lỗi trên Langfuse, xác định span nào đang mang trạng thái lỗi màu đỏ và stack trace chi tiết.
- Mitigation tạm thời:
  - Nếu lỗi `Vector store timeout` (kịch bản `tool_fail`): tắt incident bằng `python scripts/inject_incident.py --scenario tool_fail --disable` và bật chế độ degraded retrieval mode.
  - Nếu lỗi bắt nguồn từ upstream model API: cấu hình fallback provider hoặc bật retry backoff.
- Owner: `student-2A202602832`

## Alert 3

- Tên: `LowRetrievalSuccessRate`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Tỉ lệ gọi retrieval thành công (`retrieval_success_rate_pct_min: 90%`)
- Điều kiện và thời gian duy trì: `tool_success_rate_pct < 90` duy trì trong 5 phút liên tục
- Ảnh hưởng tới người dùng: Trợ lý AI không lấy được tài liệu ngữ cảnh chính xác, buộc phải trả lời dựa trên kiến thức chung hoặc fallback answer, làm giảm độ tin cậy của câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics:** Quan sát panel `Errors` trên dashboard, đối chiếu đường tỉ lệ `Retrieval success rate (%)` với ngưỡng threshold 90%.
  2. **Logs:** Lọc các event có `tool_name == "retrieval"` và `tool_success == false` trong `data/logs.jsonl`, kiểm tra tần suất xuất hiện và các query message bị ảnh hưởng.
  3. **Traces:** Mở trace tương ứng trên Langfuse, kiểm tra observation `retrieval` để xem nguyên nhân thất bại (timeout, invalid query, vector database connection refused).
- Mitigation tạm thời:
  - Tắt kịch bản lỗi nếu đang chạy test sự cố: `python scripts/inject_incident.py --scenario tool_fail --disable`.
  - Khởi động lại service retriever hoặc chuyển sang tìm kiếm từ khóa cục bộ (keyword fallback) để đảm bảo luôn cung cấp context cho LLM.
- Owner: `student-2A202602832`
