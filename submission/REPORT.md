# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trần Tuấn Hoàng
- **MSSV:** 2A202602832
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/hoangtt-vinuni/K4-L3-DAY13-TranTuanHoang-2A202602832-Monitoring-LLMOps
- **Commit SHA cuối:** 17b66d181d764a338fcf414d0f8fc4d050d5f152
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602832`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Chưa có log | **100/100** (42 records, 21 correlation IDs) | PASSED tất cả 4 hạng mục: JSON schema, Correlation ID, Log enrichment, PII scrubbing |
| `validate_dashboard.py` | Chưa có dashboard | **6/6 panel** hợp lệ | Đủ 6 panel theo contract `config/dashboard.yaml` |
| `pytest` | 22 passed | **26 passed** (100%) | Thêm 4 test PII (CCCD, credit card, passport, combined) |
| Số traces hợp lệ | 0 | **44 traces** | Tất cả trace có đủ root `lab-agent-run` + child `retrieval` + `generation` |
| Số PII leak | N/A | **0** | Regex scrub email, SĐT VN, CCCD, thẻ thanh toán, hộ chiếu + `capture_input=False` trên Langfuse |
| Latency P95 / TTFT P95 | ~150ms / ~50ms | **2654ms / 50ms** (khi rag_slow) | P95 tăng 17x do incident rag_slow (thêm 2.5s sleep); TTFT không ảnh hưởng |
| Retrieval success rate | 100% | **100%** | Không có request nào fail retrieval trong toàn bộ 32 requests đánh giá |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware`, request nhận header `x-request-id` hoặc sinh mới theo chuẩn `req-<8-char-hex>`. Sau khi gọi `clear_contextvars()`, correlation ID được gán vào `structlog` contextvars và `request.state.correlation_id`. Sau khi xử lý, ID cùng thời gian xử lý được trả về trong response header `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `user_id_hash` (được băm SHA-256 từ user_id gốc), `session_id`, `feature`, `model`, `env`, `service`, `event`, `correlation_id`, `ts`, `level`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Đăng ký processor `scrub_event` trong pipeline của `structlog` ngay trước các bước `JsonlFileProcessor` và `JSONRenderer`. Hàm `scrub_text` sử dụng regex để thay thế email, số điện thoại VN, số CCCD 12 số, số thẻ thanh toán và hộ chiếu thành các thẻ redaction dạng `[REDACTED_<TYPE>]`.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt 100/100 (không còn leak PII, đủ correlation ID và enrichment), và chạy bộ test `python -m pytest tests/test_pii.py` pass 100%.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Project Langfuse cá nhân được đặt tên đúng quy ước `day13-k4-l3b-2A202602832`, API key cấu hình trong `.env`, toàn bộ trace có metadata `user_id_hash` khớp với mã băm sinh viên.
- **Cấu trúc root/retrieval/generation observations:** Root observation mang tên `lab-agent-run` (loại agent), bên dưới gồm 2 child observations: `retrieval` (loại retriever/span) để theo dõi thời gian truy xuất tài liệu và `generation` (loại generation) để theo dõi LLM call với model, token input/output và cost. Cả 3 observations đều đặt `capture_input=False, capture_output=False` để ngăn rò rỉ PII thô.
- **Cách nối trace với log:** Sử dụng correlation_id (ví dụ: req-8f469f13 cho v1 và req-5dfe89a6 cho v2) xuất hiện đồng thời trong file log `data/logs.jsonl` và trong metadata của trace trên Langfuse.
- **Prompt name:** day13-chat
- **Version/label baseline:** Version 1 (label: baseline)
- **Version/label candidate:** Version 2 (label: candidate)
- **Trace ID của mỗi version:**
  - Baseline (v1): 0580ad7e7613eab3c6b8244915aad437 (correlation_id: req-8f469f13)
  - Candidate (v2): fd644c74d4ac40cec98d20224896bb02 (correlation_id: req-5dfe89a6)
- **Cách promote và rollback `production`:**
  - Promote: Trên Langfuse UI, dời nhãn `production` từ Version 1 sang Version 2 rồi restart API để ứng dụng nạp prompt v2.
  - Rollback: Khi cần khôi phục, dời nhãn `production` từ Version 2 quay lại Version 1 rồi restart API mà không cần sửa bất kỳ dòng code nào.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đủ 6 panel theo `config/dashboard.yaml`: Latency (P50/P95/P99, TTFT), Traffic (requests/phút), Errors (tỉ lệ lỗi tổng và retrieval success rate), Cost (tổng chi phí USD theo phút và toàn cửa sổ), Tokens (input/output tokens), Quality (mean proxy score). Mỗi panel đều có đơn vị, time range 60m UTC và đường threshold nét đứt màu đỏ.
- **SLO và lý do chọn:** Chọn mục tiêu 99.5% request hoàn thành thành công và có độ trễ latency <= 3000ms trong chu kỳ 28 ngày. Lý do chọn: baseline hệ thống xử lý trong 100-300ms, ngưỡng 3000ms đảm bảo người dùng không bị timeout trong khi vẫn có dư địa dung sai cho các truy vấn retrieval phức tạp.
- **Cách tính error budget:** Với mức SLO 99.5%, error budget là 0.5%. Nếu trong 28 ngày hệ thống phục vụ 10,000 requests thì ngân sách lỗi cho phép tối đa là 50 requests (10,000 x 0.5% = 50) bị chậm hoặc lỗi. Nếu số request vi phạm vượt quá 50, error budget cạn kiệt và đội ngũ kỹ thuật phải kích hoạt chính sách đóng băng phát hành tính năng để tập trung ổn định hệ thống.
- **Ba alert và runbook tương ứng:**
  - `HighLatencyP95`: cảnh báo khi p95(latency_ms) > 3000ms duy trì 5m; runbook tại `docs/alerts.md#alert-1`.
  - `HighErrorRate`: cảnh báo khi error_rate_pct > 2% duy trì 3m; runbook tại `docs/alerts.md#alert-2`.
  - `LowRetrievalSuccessRate`: cảnh báo khi tool_success_rate_pct < 90% duy trì 5m; runbook tại `docs/alerts.md#alert-3`.

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 11:20 - 11:40 (30/09/2026)
- **Triệu chứng từ metrics:** Panel Latency trên dashboard tăng vọt bất thường (evidence: `evidence/12-incident-metric.png`); P50/P95/P99 đều nhảy lên mức ~2651–2654ms từ baseline ~150ms; TTFT P95 vẫn duy trì bình thường ở 50ms — cho thấy bottleneck nằm sau bước khởi tạo response.
- **Log line và correlation ID liên quan:** Log `response_sent` có `latency_ms = 2652`, `tool_name = "retrieval"`, `tool_success = true`, `cost_usd = 0.001299`, mang `correlation_id = req-da651f27` (evidence: `evidence/13-incident-log.png`).
- **Trace ID và span gây ảnh hưởng:** Trace ID `9d89c64057d66c0515218b93908a5e65` (evidence: `evidence/14-incident-trace.png`); span con `retrieval` (loại RETRIEVER) chiếm 2.50s / tổng 2.65s của request; span `generation` chỉ 0.15s — xác nhận bottleneck 94% thời gian nằm ở retrieval.
- **Root cause:** Kịch bản `rag_slow` inject thêm `time.sleep(2.5)` vào hàm `retrieve()` trong `app/mock_rag.py`, mô phỏng tình huống vector database / retrieval component gặp nghẽn I/O nghiêm trọng. Điều này khiến toàn bộ pipeline bị block trước khi prompt chuyển tới LLM.
- **Fix action:** Chạy `python scripts/inject_incident.py --clear` để disable kịch bản lỗi, restart server, xác nhận latency P95 quay về mức baseline ~150ms.
- **Preventive measure:** Áp dụng alert `HighLatencyP95` (p95 > 3000ms, duration 5m) trên kênh thông báo, bổ sung timeout guard 2000ms cho bước retrieval và cơ chế fallback sử dụng cached document khi retrieval vượt ngưỡng.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt processor `scrub_event` trong structlog trước khi ghi file JSON và render, kết hợp cấu hình `capture_input=False` trên Langfuse trace. Quyết định này bảo đảm dữ liệu nhạy cảm PII (email, số điện thoại, CCCD, thẻ) không bao giờ bị rò rỉ ra log tĩnh hay hệ thống giám sát phân tán của bên thứ ba, tuân thủ nghiêm ngặt nguyên tắc Zero-PII Leakage.
- **Một lỗi/blocker đã gặp:** Gặp lỗi `[Errno 98] Address already in use` khi khởi động lại uvicorn do tiến trình cũ vẫn chiếm cổng 8000, và việc `uvicorn --reload` tự động reset các biến trạng thái runtime của kịch bản incident khi có file thay đổi.
- **Cách tìm nguyên nhân và xử lý:** Sử dụng lệnh `fuser -k 8000/tcp` để giải phóng cổng, và chạy server cố định `uvicorn app.main:app --env-file .env` (bỏ cờ `--reload`) khi thực hiện bài thi challenge để trạng thái incident không bị ngắt quãng.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics trả lời câu hỏi *"Hệ thống có vấn đề gì và bắt đầu từ lúc nào?"* $\rightarrow$ Logs trả lời câu hỏi *"Request cụ thể nào bị ảnh hưởng?"* qua `correlation_id` $\rightarrow$ Traces trả lời câu hỏi *"Nút thắt hoặc lỗi nằm ở bước/span cụ thể nào?"* $\rightarrow$ Từ đó suy ra Root Cause một cách khoa học dựa trên bằng chứng, không phải đoán mò.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt trong LLM tương đương với code trong phần mềm truyền thống; việc gắn version và label trên Langfuse cho phép kiểm soát regression và rollback tức thời mà không cần redeploy mã nguồn. Giám sát token/cost giúp ngăn ngừa bùng nổ chi phí ngoài dự kiến, còn SLO và Error Budget tạo ra ranh giới rõ ràng giữa tốc độ phát triển tính năng và độ tin cậy của dịch vụ.
- **Điều quan trọng nhất đã học:** Quy trình vận hành và quan sát một ứng dụng AI production không chỉ dừng ở việc gọi API mô hình, mà cốt lõi nằm ở khả năng truy vết nguồn gốc (observability), bảo vệ dữ liệu người dùng (PII scrubbing), và phương pháp điều tra sự cố có chuỗi bằng chứng mạch lạc.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Các kịch bản incident hiện tại dựa trên mock logic đơn giản; trong môi trường production thực tế cần tích hợp OpenTelemetry exporter chuẩn và tích hợp alert trực tiếp với webhook của PagerDuty/Slack bot.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
