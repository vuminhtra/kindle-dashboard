# Cấu hình dashboard trên Kindle — sửa 2 dòng dưới cho đúng.

# Link ảnh do GitHub Pages tạo ra (xem README, mục 2):
#   https://<username>.github.io/<tên-repo>/<SECRET_PATH>/dashboard.png
IMAGE_URL="https://USERNAME.github.io/kindle-dashboard/SECRET_PATH/dashboard.png"

# Bao nhiêu phút làm mới một lần (tối thiểu 5)
INTERVAL_MIN=30

# Ban đêm ngủ lâu hơn để tiết kiệm pin (giờ theo đồng hồ Kindle, 0–23).
# Đặt NIGHT_START=NIGHT_END để tắt chế độ này.
NIGHT_START=23
NIGHT_END=6

# Tắt Wi-Fi khi ngủ (1 = có, tiết kiệm pin; 0 = luôn bật)
WIFI_OFF_WHILE_SLEEP=1

# Cảnh báo pin yếu ở góc trên màn hình khi pin dưới mức này (%)
LOW_BATTERY=15
