# Kindle Dashboard — Lịch + Todo

Biến Kindle Paperwhite 11th gen (đã jailbreak) thành màn hình lịch Google Calendar + Google Tasks, tự cập nhật mỗi 30 phút.

```
Google Calendar + Tasks ──► GitHub Actions (render.py, mỗi 30') ──► GitHub Pages: dashboard.png ──► Kindle tải về & hiển thị
```

## 1. Lấy dữ liệu Google bằng Apps Script (~5 phút, không cần Google Cloud Console)

1. Mở <https://script.google.com> (đăng nhập **vuminhtra@gmail.com**) → **New project**, đặt tên `Kindle Dashboard`.
2. Xoá code mẫu, dán toàn bộ nội dung file `apps_script.gs`.
3. Đổi dòng `const TOKEN = 'DOI-THANH-CHUOI-BI-MAT';` thành một chuỗi ngẫu nhiên của bạn (vd `k7x2m9q4w`). Bấm **Save**.
4. Bên trái, mục **Services** → dấu **+** → chọn **Google Tasks API** → **Add**.
5. Chọn hàm `testCollect` ở thanh trên → **Run** → cho phép quyền (Google báo *app chưa xác minh* → **Advanced → Go to Kindle Dashboard (unsafe)** → **Allow**; đây là script của chính bạn). Xem *Execution log* có danh sách lịch/việc là được.
6. **Deploy → New deployment** → bánh răng → **Web app**:
   - *Execute as*: **Me**
   - *Who has access*: **Anyone**
   → **Deploy** → copy **Web app URL** (dạng `https://script.google.com/macros/s/…/exec`).
7. Ghép link: `DATA_URL = <Web app URL>?token=<TOKEN của bạn>`. Dán vào trình duyệt thử — thấy JSON là đúng.

> Sửa code Apps Script sau này: **Deploy → Manage deployments → ✏️ → Version: New version → Deploy** (URL giữ nguyên).
> Cách cũ (OAuth + `get_token.py`) vẫn dùng được nếu không đặt `DATA_URL`.

## 2. Đưa lên GitHub

1. Vào <https://github.com/new> → *Repository name* `kindle-dashboard` → **Public** → **Create repository**.
2. Trang repo mới → link **uploading an existing file** → kéo **toàn bộ nội dung** thư mục `kindle-dashboard` (gồm cả thư mục `.github`) vào → **Commit changes**.
   Nếu Windows không kéo được thư mục `.github`: bấm **Add file → Create new file**, gõ tên `.github/workflows/update.yml`, dán nội dung file đó → Commit.
3. **Settings → Secrets and variables → Actions → New repository secret**:
   - `DATA_URL` = link ở bước 1.7
   - `SECRET_PATH` = chuỗi ngẫu nhiên khác, vd `p3n8v1z6`
4. (Tuỳ chọn) tab **Variables**: `DASH_SKIP_CALENDARS` = tên lịch muốn ẩn, vd `iPhone`.
5. **Settings → Pages → Source: GitHub Actions**.
6. Tab **Actions** → bật workflow nếu được hỏi → **Cập nhật dashboard Kindle → Run workflow**. Xong (dấu ✓ xanh), ảnh ở:
   `https://<username>.github.io/kindle-dashboard/<SECRET_PATH>/dashboard.png`

## 3. Cài lên Kindle (sau khi jailbreak bằng AdBreak)

Jailbreak đời mới (AdBreak) dùng **scriptlet** (file `.sh` trong `documents`), không dùng KUAL.

1. Mở `kindle/dashboard/config.sh`, sửa `IMAGE_URL` thành link ảnh ở bước 2.
   Tuỳ chọn: `INTERVAL_MIN` (mặc định 30 phút), giờ ngủ đêm `NIGHT_START`/`NIGHT_END`, `LOW_BATTERY`.
2. Cắm Kindle vào máy tính, chép:
   - thư mục `kindle/dashboard/` → **gốc ổ Kindle** (thành `E:\dashboard\`)
   - file `kindle/documents/Dashboard.sh` → `E:\documents\`
3. Rút cáp. Trong Thư viện sẽ có “sách” **Dashboard Lich & Todo** → bấm vào để bật.
   Kindle tắt giao diện, hiện dashboard, rồi cứ `INTERVAL_MIN` phút tự bật Wi-Fi, tải ảnh mới, tắt Wi-Fi và ngủ.
4. **Thoát về Kindle bình thường:** giữ nút nguồn ~40 giây cho máy khởi động lại (dashboard không tự chạy lại).
5. Lỗi gì xem `E:\dashboard\log.txt`.

Ghi chú:
- Chế độ đêm dùng đồng hồ của Kindle; nếu giờ Kindle lệch, chỉnh `NIGHT_START/NIGHT_END` hoặc đặt bằng nhau để tắt.
- Pin dưới `LOW_BATTERY`% sẽ hiện dòng “PIN YEU” ở góc trên.
- Cách tắt giao diện và đánh thức bằng RTC dựa theo [usetrmnl/trmnl-kindle](https://github.com/usetrmnl/trmnl-kindle) (MIT); chưa được thử trên chính Paperwhite 11 firmware 5.18.2.

## Chạy thử trên máy

```bash
pip install pillow requests
python render.py --sample sample.json --now 2026-11-03T13:00 --out preview.png
```

Tuỳ chỉnh: múi giờ `DASH_TZ` (mặc định `Asia/Ho_Chi_Minh`), vị trí thời tiết `DASH_LAT`/`DASH_LON` (mặc định Nha Trang), giao diện trong hàm `render()` của `render.py`.

Font: Inter (SIL Open Font License) — workflow tự tải từ [rsms/inter](https://github.com/rsms/inter/releases) khi chạy; chạy thử trên máy thì tải 4 file `Inter-{Regular,Medium,SemiBold,Bold}.otf` bỏ vào thư mục `fonts/`.
