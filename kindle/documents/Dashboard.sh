#!/bin/sh
# Name: Dashboard Lich & Todo
# Author: Tra

# Bấm vào "sách" này trong thư viện để bật màn hình dashboard.
# Muốn quay lại Kindle bình thường: bấm nút nguồn 1 lần (không được thì giữ ~40 giây).

DIR=/mnt/us/dashboard

if [ ! -f "$DIR/loop.sh" ] || [ ! -f "$DIR/config.sh" ]; then
  echo "Thieu thu muc /mnt/us/dashboard (loop.sh, config.sh)."
  echo "Chep thu muc 'dashboard' vao goc o Kindle roi thu lai."
  exit 1
fi

. "$DIR/config.sh"
case "$IMAGE_URL" in
  *USERNAME*|*SECRET_PATH*|"")
    echo "Chua sua IMAGE_URL trong dashboard/config.sh"
    exit 1 ;;
esac

if pgrep -f "$DIR/loop.sh" >/dev/null 2>&1; then
  echo "Dashboard dang chay roi."
  exit 0
fi

echo "Dang bat dashboard..."
echo "Thoat: bam nut nguon 1 lan."
sleep 3
# chạy nền, tách khỏi tiến trình giao diện để không bị dừng theo
if command -v setsid >/dev/null 2>&1; then
  setsid sh "$DIR/loop.sh" >/dev/null 2>&1 < /dev/null &
else
  nohup sh "$DIR/loop.sh" >/dev/null 2>&1 < /dev/null &
fi
exit 0
