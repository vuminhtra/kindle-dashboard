# Cấu hình dashboard trên Kindle — sửa 2 dòng dưới cho đúng.

# Link ảnh do GitHub Pages tạo ra (xem README, mục 2):
#   https://<username>.github.io/<tên-repo>/<SECRET_PATH>/dashboard.png
IMAGE_URL="https://USERNAME.github.io/kindle-dashboard/SECRET_PATH/dashboard.png"

# Bao nhiêu phút làm mới một lần ban ngày (tối thiểu 5)
INTERVAL_MIN=15

# Ban đêm làm mới thưa hơn để tiết kiệm pin (giờ theo đồng hồ Kindle, 0–23).
# Đặt NIGHT_START=NIGHT_END để tắt chế độ này.
NIGHT_START=0
NIGHT_END=8
# Ban đêm bao nhiêu phút làm mới một lần (0 = ngủ thẳng tới NIGHT_END)
NIGHT_INTERVAL_MIN=240

# Tắt Wi-Fi khi ngủ (1 = có, tiết kiệm pin; 0 = luôn bật)
WIFI_OFF_WHILE_SLEEP=1

# Cảnh báo pin yếu ở góc trên màn hình khi pin dưới mức này (%)
LOW_BATTERY=15
