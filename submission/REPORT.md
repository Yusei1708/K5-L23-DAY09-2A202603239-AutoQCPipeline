# Báo cáo Day 09 — Vũ Văn Thắng, 2A202603239

## 1. Kết luận trước

Pipeline kết luận **`HOLD`** (mã thoát `10`). Trong tổng số **`224` ảnh thô** (`data/raw`), bước `intake` loại **`22` ảnh** (`9.8%` gồm `8` trùng byte, `5` rò rỉ tập test, `4` gần trùng, `3` kích thước nhỏ, `2` ảnh hỏng) và nhận **`202/224` ảnh**. Qua các vòng QC + sửa tự động + người duyệt mô phỏng (`80/125` ảnh hàng đợi), toàn bộ **`36` lỗi bắt buộc ban đầu** đã về **`0` lỗi `ERROR`**, nhưng vẫn còn **`38/202` ảnh (`18.81% >= ngưỡng 10.00%`)** mang cảnh báo chưa được duyệt nên gate chặn phát hành chính thức và chỉ xuất **bản NHÁP** tại `submission/export/clean_v1/` (`decision: Hold`).

## 2. Lỗi và phân việc

Bảng tổng hợp toàn bộ **`211` dòng lỗi/cảnh báo** trong `submission/reports/02_error_list_v1` (mẫu số intake: `224` ảnh; mẫu số QC vòng 1 trên phần còn lại: `202` ảnh; tổng box xuất sau pipeline ở `class_stats.csv`: `748` box):

| Mã lỗi | Số dòng / ảnh | Ai sửa | Vì sao |
|---|---:|---|---|
| `DUP_IMAGE_EXACT` | `8` dòng / `8` ảnh (`8/224`) | Máy (`intake` + `autofix`) | Trùng md5 từng byte với ảnh đứng trước; loại hẳn khỏi bản sao `ds` theo thứ tự tên |
| `LEAK_TEST` | `5` dòng / `5` ảnh (`5/224`) | Máy (`intake` + `autofix`) | Trùng `test/test_*` (`img_0049, 0101, 0167, 0174, 0221`); chặn sớm để không làm sai lệch đánh giá |
| `DUP_IMAGE_NEAR` | `4` dòng / `4` ảnh (`4/224`) | Máy (`intake` + `autofix`) | Gần trùng qua perceptual hash (`phash <= 10`: `img_0076, 0143, 0186, 0223`) |
| `BAD_SIZE` | `3` dòng / `3` ảnh (`3/224`) | Máy (`intake` + `autofix`) | Cạnh ngắn `< 250 px` (`180–226 px` ở `img_0107, 0113, 0122`); loại ở cửa vào |
| `CORRUPT_IMAGE` | `2` dòng / `2` ảnh (`2/224`) | Máy (`intake` + `autofix`) | Không giải mã được hoặc cắt cụt khi `load()` (`img_0010, img_0136`) |
| `BAD_CLASS_NAME` | `2` dòng / `data.yaml` | Máy (`autofix`) | Chuẩn hoá `'Person'`, `'Bus'` trong `data.yaml` về đúng `cfg["classes"]` |
| `BOX_OUT_OF_IMAGE` | `8` dòng / `8` ảnh (`8/202`) | Máy (`autofix`) | Quy tắc hình học thuần tuý: cắt toạ độ vượt `[0, 1]` vượt `0.002` về mép ảnh (`clip_box`) |
| `DUP_BOX` | `7` dòng / `7` ảnh (`7/202`) | Máy (`autofix`) | Hai box cùng lớp `IoU > 0.9` trên cùng ảnh; xoá an toàn dòng trùng đứng sau (`drop_line`) |
| `BAD_CLASS_ID` | `6` dòng / `6` ảnh (`6/202`) | Máy (`autofix`) | ID ngoài `0..3` (`93, -1, 7, 4`); xoá dòng hỏng (`drop_line`), tránh làm Ultralytics loại cả ảnh |
| `BOX_ZERO` | `4` dòng / `4` ảnh (`4/202`) | Máy (`autofix`) | Chiều rộng hoặc cao `<= 0` (vd. `img_0050.txt:1` có `w=0.0`); xoá dòng vô nghĩa |
| `BAD_FORMAT` | `3` dòng / `3` ảnh (`3/202`) | Máy (`autofix`) | Thiếu cột hoặc chứa `nan` (`img_0014, 0022, 0179`); xoá dòng lỗi cú pháp |
| `MISSING_LABEL_FILE` | `6` dòng / `6` ảnh (`6/202`) | **Người** (`05_review_queue`) | Máy không được phép bịa nhãn (`autofix` chỉ ghi `needs_label`); thiếu 1 file -> `Rework` |
| `POSSIBLE_MISSING` | `53` dòng / `52` ảnh (`52/202`) | **Người** (`hàng đợi`) | Chỉ là ý kiến thứ hai của `yolo26l` (`conf >= 0.6`); cần mắt người xác nhận vật thật |
| `POSSIBLE_FALSE_POS` | `29` dòng / `27` ảnh (`27/202`) | **Người** (`hàng đợi`) | Box nhãn không khớp dự đoán nào (`IoU < 0.3`), có thể là thừa hoặc vật `yolo26l` sót |
| `POSSIBLE_LOOSE_BOX` | `28` dòng / `24` ảnh (`24/202`) | **Người** (`hàng đợi`) | Cùng lớp nhưng `IoU < 0.5`; ranh giới ôm sát phụ thuộc guideline |
| `POSSIBLE_WRONG_CLASS` | `18` dòng / `18` ảnh (`18/202`) | **Người** (`hàng đợi`) | Nhầm ngữ nghĩa giữa `car/truck/bus/person` (`IoU >= 0.5`); máy không được tự đổi lớp |
| `EMPTY_LABEL` | `12` dòng / `12` ảnh (`12/202`) | **Người** (`hàng đợi`) | Phân biệt ảnh nền sạch vs ảnh bị xoá nhầm hết nhãn (tăng lên `15` ảnh ở v2 sau `drop_line`) |
| `BOX_TINY` | `6` dòng / `4` ảnh (`4/202`) | **Người** (`hàng đợi`) | Cạnh ngắn `< 12 px` (tăng lên `7` dòng / `5` ảnh ở v2 sau khi `clip_box` `img_0030` còn `9.8 px`) |
| `CLASS_RARE` | `4` dòng / `<dataset>` | Máy theo dõi → **Máy xoá** | Gây ra bởi `4` ID lạ (`-1, 4, 7, 93`); biến mất tự nhiên ở v2 sau `drop_line` |
| `BOX_HUGE` | `3` dòng / `3` ảnh (`3/202`) | **Người** (`hàng đợi`) | Box phủ `> 95%` ảnh (có thể đúng cho ảnh cận cảnh như `img_0128`) |

- **Cách `05_review_queue.csv` xếp hàng và hiệu quả ngân sách `80` ảnh:** Hàm `build_queue` cộng dồn trọng số rủi ro (`NEEDS_LABEL=10`, `POSSIBLE_WRONG_CLASS=3*(1+conf)`, `POSSIBLE_MISSING=2*(1+conf)`, `POSSIBLE_FALSE_POS=2`, `FIXED_DROP_LINE=2`, `POSSIBLE_LOOSE_BOX=1.5*(1+conf)`...), nên đưa ảnh đa lỗi nặng `img_0020` (`11.524`) và toàn bộ `6` ảnh `MISSING_LABEL_FILE` (`10.0`) lên đầu hàng, đẩy `BOX_TINY`/`BOX_HUGE` đơn lẻ (`0.3`–`0.9`) xuống cuối. Với ngân sách **`80/125` ảnh hàng đợi (`64.0%`)**, người duyệt đã xử lý **`6/6` (`100%`) `MISSING_LABEL_FILE`**, **`18/18` (`100%`) `POSSIBLE_WRONG_CLASS`**, **`50/52` (`96.2%`) `POSSIBLE_MISSING`**, **`12/23` (`52.2%`) `POSSIBLE_FALSE_POS`** và **`8/24` (`33.3%`) `POSSIBLE_LOOSE_BOX`** trong `04_error_list_v2`; để lại `45` ảnh cuối (`81–125`), trong đó **`38` ảnh** vẫn còn cảnh báo `WARN` sang vòng 3 (`18.81% >= 10%` → `Hold`).

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) trên `data/calib` | Lý do (đánh đổi) |
|---|---:|---:|---|---|
| `duplicates.phash_dist` | `2` | **`10`** | `EXACT`: `1.00/1.00 -> 1.00/1.00`<br>`NEAR`: `1.00/0.50 -> 1.00/0.67` (F1 `0.67 -> 0.80`) | Tăng từ `2` lên `10` giữ `Precision = 1.00` (không xoá oan ảnh tốt), đồng thời trên `raw` bắt thêm cặp gần trùng `img_0186` vs `img_0061` (`phash dist = 10`). Không chọn `16` (F1 cao nhất `0.91` trên calib) vì `16` phá precision trên ảnh thật |
| `second_opinion.conf` | `0.25` | **`0.60`** | `MISSING`: `0.50/1.00 -> 0.57/1.00` (F1 `0.67 -> 0.73`)<br>`WRONG_CLASS`: `0.56/0.83 -> 0.62/0.83` (F1 `0.67 -> 0.71`)<br>`LOOSE_BOX`: `0.29/0.40 -> 0.20/0.20`<br>`FALSE_POS`: `0.31/1.00 -> 0.31/1.00` | Bảo toàn **100% recall `MISSING`** và **83% recall `WRONG_CLASS`** nhưng loại bớt báo động giả điểm thấp (rút hàng đợi `143 -> 125` ảnh, giảm tỉ lệ chưa duyệt `28.71% -> 18.81%` mà không cố nâng lên `0.7–0.8` gây rớt recall `MISSING` còn `0.88–0.75`). Chấp nhận đánh đổi giảm recall `LOOSE_BOX` trên calib từ `2/5` xuống `1/5` |

- **Hai chỗ `calibration` có thể đánh lừa (kèm bằng chứng từ dữ liệu):**
  1. **Chọn `F1` cao nhất trên `calib` làm bùng nổ xoá oan `LEAK_TEST` trên `raw`:** Trên `calibration_report.md`, `phash_dist = 16` đạt F1 đỉnh **`0.91`** (`DUP_IMAGE_NEAR` P=`1.00`, R=`0.83`), **nhưng `data/calib/MANIFEST.csv` có `0` ca `LEAK_TEST` nên `calibrate.py` bỏ qua hoàn toàn `LEAK_TEST` phát sinh!** Kiểm tra thực tế cho thấy ngay tại `phash_dist = 16`, `duplicates` đã cờ nhầm **`1` ảnh `calib` là `LEAK_TEST`** và trên `data/raw` gây **`8` vụ xoá nhầm ảnh khác nhau hoàn toàn**: ghép nhầm `img_0011` (tennis) trùng `img_0008` (trượt tuyết, `dist=16`), và đánh dấu oan `6` `LEAK_TEST` giả như `img_0013` (bàn làm việc laptop) trùng `test/test_087.jpg` (sân bóng chày). Ở `phash_dist = 10`, cả 4 cặp `DUP_IMAGE_NEAR` (`img_0076/0042` `dist=0`, `img_0143/0037` `dist=0`, `img_0223/0077` `dist=6`, `img_0186/0061` `dist=10`) và `5` cặp `LEAK_TEST` đều khớp mắt người `100%`.
  2. **Lệch phân bố lỗi giữa `calib` (`39` ảnh) và `raw` (`224` ảnh):** `WRONG_CLASS` ở `calib` phần lớn là `person->car`, trong khi ở `raw` chủ yếu là `car/truck/bus` dễ nhầm ngay cả với `yolo26l` (`img_0078, img_0083, img_0220` vẫn bị `yolo26l` nghi `truck -> car` sau khi người duyệt đã sửa chuẩn).

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

- **(a) Chứng minh cửa chặn hoạt động thật (`--budget 0`):** Chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` cho kết luận **`REWORK`** với mã thoát **`20`** (`còn 6 lỗi bắt buộc (ERROR), chặn phát hành; 112/202 ảnh còn cảnh báo chưa duyệt (55.45%)`), nhật ký bước 5 ghi rõ `KHÔNG xuất` và thư mục `work/exp_nb/clean_v1` không tồn tại.
- **(b) Các điểm mù có bằng chứng từ ảnh (`work/viz/` & `work/viz_ds/`):**
  1. **Mù kép giữa nhãn thô và `yolo26l`:** Ở `img_0083.png`, người chăn cừu bên trái đường không có box nhưng `yolo26l` không vượt ngưỡng `0.6` nên không hề có cảnh báo `POSSIBLE_MISSING`; ở `img_0220.png`, sau khi đã qua mắt người, chính `yolo26l` vẫn nhầm xe bán tải `truck` thành `car` (`conf=0.71`, đồng thời bỏ sót người mặc áo sọc đứng sát mép trái ảnh).
  2. **Box lỏng nhẹ / gộp người rớt ngoài ngân sách 80 & vật nhỏ `< 600 px²`:** Ở `img_0015.png` (hạng ~88, ngoài ngân sách 80 do `conf=0.6` khiến priority còn `2.841`), box `3:person` cắt nửa người và gộp nhầm vận động viên đánh bóng với trọng tài vẫn đi thẳng vào `clean_v1`; ở `img_0078.png`, xe con bạc và nhóm người đi bộ bên kia đường nhỏ hơn `min_area_px = 600` (`>= 12 px` theo chiều đơn lẻ nhưng diện tích nhỏ) nên thoát cả `label_format` lẫn `second_opinion`; ở `img_0160.png`, cả chục đầu xe tải san sát không được gán hết dù đã qua duyệt. Ngoài ra, ảnh cắt `> 50%` rồi thu nhỏ (`2/6` bẫy nặng ở `calib`) vượt `phash_dist = 10` không thể bắt mà không gây báo động giả.

## 5. Train: raw vs clean (tùy chọn)

Đã thực hiện thí nghiệm đối chứng công bằng trên **Google Colab CPU runtime** (do máy cá nhân quá nhiệt ở `imgsz=640` GPU và Colab T4 lúc chạy báo hết backend GPU HTTP `503`), dùng đúng `scripts/train_compare.py` với cùng siêu tham số rút gọn đồng nhất giữa hai biến thể ([docs/COLAB.md](../docs/COLAB.md)): **`model=yolo26n.pt`**, **`epochs=10`**, **`imgsz=320`**, **`batch=8`**, **`device=cpu`**, **`2` seed (`0`, `1`)**, cùng tập `val` (`data/gold_val`, `40` ảnh) và tập `test` (`data/test`, `100` ảnh, `387` vật thể).

- **Số ảnh thực train:** Tập `raw` nạp `224` ảnh nhưng Ultralytics tự loại **`11` ảnh lỗi/hỏng** (`img_0010, 0014, 0020, 0022, 0099, 0104, 0117, 0136, 0179, 0194, 0199`) → **thực train `213` ảnh** (`19` ảnh nền); tập `clean` (`clean_v1`) **thực train `202` ảnh** (`0` corrupt, `4` ảnh nền, `manifest_sha1 = 2215edeb...`).

Bảng tổng hợp từ `submission/results/comparison.md` (biểu đồ ở `submission/results/comparison.png`):

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.518 ± 0.044 | 0.342 ± 0.023 | 0.645 ± 0.038 | 0.467 ± 0.004 |
| clean | 202 | 2 | 0.534 ± 0.005 | 0.347 ± 0.016 | 0.695 ± 0.035 | 0.472 ± 0.009 |

Chênh mAP50 (clean − raw) = **+0.016**.

*(Chi tiết từng seed: `raw_seed0 mAP50=0.5489`, `raw_seed1 mAP50=0.4868`; `clean_seed0 mAP50=0.5301`, `clean_seed1 mAP50=0.5370`. Theo lớp TB 2 seed: `car` `0.482 -> 0.506`, `person` `0.677 -> 0.677`, `truck` `0.459 -> 0.446`, `bus` `0.453 -> 0.505`.)*

- **So sánh với độ nhiễu & kết luận trung thực:** Độ chênh **`+0.016` nhỏ hơn hẳn độ lệch chuẩn giữa 2 seed của `raw` (`±0.044`)** và khoảng giá trị chồng lấn nhau (`raw_seed0 = 0.5489` thậm chí cao hơn cả 2 seed của `clean`). Do đó, ở thiết lập 2 seed này **chưa thể kết luận chắc chắn "`clean` cho mAP cao hơn `raw`"** — tín hiệu ổn định hơn ở `clean` là **Precision tăng rõ (`0.645 -> 0.695`, `+0.050`)** và **độ dao động giữa seed giảm mạnh (`std mAP50` từ `0.044` xuống `0.005`)**.
- **Nguyên nhân kỹ thuật khả dĩ & cách kiểm tiếp theo:**
  1. **`5` ảnh rò rỉ `LEAK_TEST` trong `raw` (`img_0049, 0101, 0167, 0174, 0221`):** Trùng với `test/` làm điểm đánh giá của `raw` bị nâng giả tạo (đặc biệt ở `raw_seed0`), che khuất lợi thế của `clean`; kiểm chứng bằng cách chạy thêm biến thể `raw_no_leak` bỏ riêng `5` ảnh này trên cùng 2 seed.
  2. **Tập `clean_v1` mới ở trạng thái `Hold` (`38/202` ảnh cảnh báo ngoài ngân sách `80` chưa duyệt) + cấu hình rút gọn `imgsz=320, epochs=10`:** Vẫn còn lỗi box lỏng (`img_0015`) và sót vật nhỏ (`img_0078, 0160`), lại nén xuống `320 px` trên tập test chỉ `100` ảnh nên phương sai đánh giá cao (ví dụ `truck` chỉ có ít mẫu test nên dao động); kiểm chứng bằng biến thể chuẩn trên `oracle` (`scripts/train_compare.py --variants oracle`) và tăng lên `>= 3–5` seed ở `640 px × 20–40 epoch` khi có GPU T4, đồng thời duyệt bổ sung phần dư hàng đợi để lên `Release`.

## 6. Quyết định, ghi chú AI và phần thưởng

- **(a) Quyết định cuối (`HOLD`) & điều kiện lên `Release`:** Giữ nguyên **`HOLD`** (`0` lỗi bắt buộc, `38/202 = 18.81% >= 10.00%` ảnh còn cảnh báo chưa duyệt). Để chuyển thành `Release`, đội duyệt cần kiểm tra thêm tối thiểu **`18` ảnh** đứng đầu phần dư của `05_review_queue.csv` (dòng `81–99`: `img_0012, img_0210, img_0032` và các ảnh `POSSIBLE_LOOSE_BOX`) thông qua luồng `--no-review` + `--resume-after-review` sao cho số ảnh cảnh báo chưa duyệt giảm xuống **`<= 20/202` (`< 10%`)**.
- **(b) Ghi chú AI:** Không dùng. Toàn bộ `label_format.py`, `gate.py`, `autofix.py`, `second_opinion.py` và check thưởng tự viết đều bám sát docstring hợp đồng vào/ra, giữ nguyên 100% file ghim SHA1 trong `scripts/_protected.json` và được kiểm chứng bằng `83` unit test + kiểm tra trực tiếp trên ảnh/báo cáo của `data/raw` và `data/calib`.
- **Thưởng +3 (Check mới độc lập + test):** Viết [pipeline/checks/aspect_ratio.py](../pipeline/checks/aspect_ratio.py) kèm [tests/test_aspect_ratio.py](../tests/test_aspect_ratio.py) (`4/4` test pass, không sửa `pipeline/checks/__init__.py` để giữ nguyên SHA1). Check phát hiện **`7` box** lệch tỉ lệ khung hình pixel `max(w/h, h/w) > 6.0` (`BOX_EXTREME_AR`) trên `work/run/ds/` từ `6.59:1` đến `9.84:1`, điển hình là dải mảnh `9.8 x 84.3 px` ở `img_0030` dòng 9 và `13.5 x 133.2 px` ở `img_0155` dòng 2.
- **Thưởng +2 (CVAT [docs/CVAT_FILTER.md](../docs/CVAT_FILTER.md)):** Tạo Project `day09-2A202603239` (Project `#5` từ [cvat/labels.json](../cvat/labels.json)), Task `#23` (`filter-box-tiny`, `20` ảnh gồm đầu hàng đợi `05_review_queue.csv` + các ảnh `BOX_TINY`, import `YOLO 1.1`) trên CVAT local và chụp bằng chứng [submission/cvat_filter.png](cvat_filter.png). Khi bật lọc `width < 20`: **`img_0026.jpg`** (frame 2) khớp **`6` box** `person` (`11.4–19.9 px`, trong khi `BOX_TINY < 12 px` của pipeline chỉ gắn cờ `1` box `11.4 px` ở dòng 6); **`img_0161.jpg`** (frame 15) khớp **`3` box** `#91, #92, #93` (khớp `3/3` với `BOX_TINY` dòng `2, 3, 4`: `10.3, 11.4, 11.9 px`); thử lọc `label=="truck"` nhảy đúng tới `img_0020.jpg` (`Items: 1`). Thuộc tính **`can_review`**: người gán tích dấu ngay trên giao diện CVAT khi gặp ca mơ hồ cần người thứ hai xem lại; trong pipeline tự động Day 09, vai trò đó do các cờ `WARN` (`second_opinion`, `BOX_TINY`, `BOX_HUGE`) đảm nhiệm để đẩy ảnh vào hàng đợi ưu tiên `05_review_queue.csv`.
