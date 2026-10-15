# Reflection (≤1 page)

### Which fault types were hardest to catch, and why?

Trong quá trình bảo vệ data pipeline qua 3 pha (Practice, Public và Private), các lỗi khó phát hiện nhất là nhóm **subtle faults** ở cả 4 pillars, đặc biệt là:

1. **Subtle Feature Skew & Embedding Drift (`ai_infra`):**
   - Các trường hợp drift tinh vi (subtle) có giá trị dịch chuyển centroid (`centroid_shift` ~ 0.028 - 0.031) hoặc tuổi tài liệu (`avg_doc_age_days` ~ 31.8 - 37.6 ngày) nằm hoàn toàn bên trong khoảng dao động tự nhiên của luồng dữ liệu sạch (clean events có `centroid_shift` lên tới 0.0387 và `doc_age` lên tới 37.5 ngày).
   - Với hàm chấm điểm phạt nặng False Positive ($0.5 \cdot \text{TPR} - 0.3 \cdot \text{FPR}$), bất kỳ sự hạ thấp ngưỡng đơn biến nào để cố bắt các ca subtle này đều dẫn đến việc báo động nhầm (false alarms) trên hàng loạt clean batches, làm suy giảm nghiêm trọng điểm số tổng thể. Riêng đối với `feature_materialization`, việc thiết lập khoảng cách an toàn (margin) ở mức `0.50` sigma đã phân tách thành công giữa clean variance (cao nhất ~0.414) và subtle shift (thấp nhất ~0.970), giúp bắt trọn 100% feature skew mà không sinh ra bất kỳ false alarm nào.

2. **Subtle Distribution Shift & Volume Drop (`checks`):**
   - Các lỗi `volume_drop` (ví dụ `row_count` 469 hay 474) và `distribution_shift` nhẹ (`mean_amount` ~ 85.72) nằm trọn trong khoảng dung sai $\pm 3\sigma$ của baseline tĩnh (`row_count` $\in [435.5, 561.3]$, `mean_amount` $\in [72.8, 90.6]$). Nhìn nhận từng batch riêng lẻ không thể phát hiện được sự suy giảm này mà không gây ra false positive cho các batch bình thường có độ lệch ngẫu nhiên tương đương.

3. **Subtle Runtime Anomaly (`lineage`):**
   - Thời gian thực thi runtime kéo dài nhẹ (4480 - 4740ms) vẫn thấp hơn ngưỡng baseline `lineage_duration_ms_max` (5134.98ms). Trong khi đó, các lỗi cấu trúc như `missing_upstream` (thiếu `raw.customers`) và `orphan_output` (`actual_downstream_count == 0`) lại rất rõ ràng và được bắt chính xác 100%.

---

### What would you change about your cost/coverage tradeoff, if you had another pass?

1. **Tận dụng bộ nhớ trạng thái (`ctx.state`) để theo dõi thống kê chuỗi thời gian (Sequential/Rolling Tracking):**
   - Thay vì chỉ đánh giá độc lập từng event snapshot theo ngưỡng tĩnh, ta có thể lưu trữ rolling window (5–10 batches gần nhất) cho từng bảng dữ liệu hoặc corpus.
   - Ứng dụng các thuật toán như CUSUM (Cumulative Sum) hoặc Exponential Moving Average (EMA) để phát hiện các độ lệch nhỏ tích lũy (subtle drift / volume drop) kéo dài qua nhiều chu kỳ mà không sợ bị nhiễu cục bộ của một batch đơn lẻ.

2. **Cơ chế kiểm tra phân tầng động (Dynamic Hierarchical Metering) để tối ưu ngân sách:**
   - Ở pha Private với ngân sách 320 credits cho 200 events, chiến lược full single-pass coverage tiêu tốn đúng 300 credits và có độ dư an toàn (overage = 0). Tuy nhiên ở pha Public (ngân sách 220 credits cho 160 events), full pass sẽ tiêu tốn 240 credits (overage ~0.09).
   - Nếu có thêm cơ hội, tôi sẽ xây dựng cơ chế phân tầng dựa trên ngân sách còn lại (`ctx.tools.budget_remaining()`): đối với các tool đắt đỏ (như `feature_drift` và `embedding_drift` tốn 2.0 credits), chỉ kích hoạt kiểm tra sâu khi luồng dữ liệu upstream có dấu hiệu bất thường (ví dụ: batch trước đó vừa có cảnh báo về volume hoặc freshness), giúp tiết kiệm 15–20% credit mà vẫn đảm bảo độ phủ cao ở những vùng rủi ro.
