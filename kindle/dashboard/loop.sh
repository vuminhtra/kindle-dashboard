#!/bin/sh
# Vòng lặp dashboard: bật Wi-Fi → tải PNG → hiển thị bằng eips → tắt Wi-Fi → ngủ (RTC) → lặp lại.
# Được chạy nền bởi documents/Dashboard.sh. Dừng: giữ nút nguồn ~40 giây để khởi động lại Kindle.
# Cách tắt giao diện, đánh thức bằng RTC dựa theo usetrmnl/trmnl-kindle (MIT).

DIR="${DASH_DIR:-/mnt/us/dashboard}"
LOG="$DIR/log.txt"
IMG="/tmp/dashboard.png"
. "$DIR/config.sh"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
  # giữ log nhỏ
  if [ "$(wc -c < "$LOG")" -gt 200000 ]; then tail -n 300 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"; fi
}

wifi() { lipc-set-prop com.lab126.cmd wirelessEnable "$1" 2>/dev/null; }

battery() {
  b=$(lipc-get-prop com.lab126.powerd battLevel 2>/dev/null)
  [ -n "$b" ] || b=$(lipc-get-prop com.lab126.powerd status 2>/dev/null | grep "Battery Level:" | cut -d: -f2 | tr -d '% ')
  echo "${b:-100}"
}

init() {
  log "=== Khởi động dashboard ==="
  # Tắt giao diện Kindle để icon trạng thái không vẽ đè lên ảnh và cho phép ngủ sâu.
  /etc/init.d/framework stop 2>/dev/null || {
    stop framework >/dev/null 2>&1 || initctl stop framework >/dev/null 2>&1
    stop lab126_gui >/dev/null 2>&1
  }
  initctl stop webreader >/dev/null 2>&1
  { echo powersave > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor; } 2>/dev/null
  lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
}

wait_net() {
  # chờ tối đa 45 giây đến khi có Internet
  i=0
  while [ $i -lt 45 ]; do
    curl -s -m 5 -o /dev/null -I "$IMAGE_URL" && return 0
    sleep 1
    i=$((i + 1))
  done
  return 1
}

fetch_and_show() {
  wifi 1
  if ! wait_net; then
    log "Không có mạng"
    wifi 0; sleep 15; wifi 1          # thử bật lại Wi-Fi một lần
    wait_net || { eips 1 1 "Khong co Wi-Fi - se thu lai sau"; return 1; }
  fi
  rm -f "$IMG"
  # thêm ?t=... để không bị bộ nhớ đệm CDN trả ảnh cũ
  curl -s -L -m 60 -o "$IMG" "$IMAGE_URL?t=$(date +%s)"
  if [ ! -s "$IMG" ]; then
    log "Tải ảnh thất bại"
    eips 1 1 "Tai anh that bai - se thu lai sau"
    return 1
  fi
  eips -c
  sleep 1
  eips -g "$IMG"
  b=$(battery)
  if [ "$b" -lt "${LOW_BATTERY:-15}" ] 2>/dev/null; then
    eips 1 1 "PIN YEU ${b}% - HAY SAC"
  fi
  log "Đã cập nhật (pin ${b}%)"
  return 0
}

sleep_secs() {
  mins=${INTERVAL_MIN:-30}
  [ "$mins" -ge 5 ] 2>/dev/null || mins=5
  h=$(date +%H | sed 's/^0//'); h=${h:-0}
  ns=${NIGHT_START:-23}; ne=${NIGHT_END:-6}
  if [ "$ns" != "$ne" ]; then
    night=0
    if [ "$ns" -gt "$ne" ]; then { [ "$h" -ge "$ns" ] || [ "$h" -lt "$ne" ]; } && night=1
    else { [ "$h" -ge "$ns" ] && [ "$h" -lt "$ne" ]; } && night=1; fi
    if [ $night -eq 1 ]; then
      # ngủ tới giờ NIGHT_END (tính theo giờ tròn)
      left=$(( (ne - h + 24) % 24 ))
      [ $left -eq 0 ] && left=24
      echo $(( left * 3600 - $(date +%M | sed 's/^0//;s/^$/0/') * 60 ))
      return
    fi
  fi
  echo $(( mins * 60 ))
}

go_to_sleep() {
  secs=$1
  [ "${WIFI_OFF_WHILE_SLEEP:-1}" = 1 ] && wifi 0
  log "Ngủ ${secs}s"
  sleep 10   # chờ màn hình vẽ xong; cũng là khoảng để dừng script nếu cần
  [ -n "$DASH_ONCE" ] && exit 0
  RTC=/sys/class/rtc/rtc1
  [ -d "$RTC" ] || RTC=/sys/class/rtc/rtc0
  # đặt báo thức RTC rồi ngủ sâu; nếu không được thì sleep thường
  { echo 0 > "$RTC/wakealarm" &&
    echo "+${secs}" > "$RTC/wakealarm" &&
    echo mem > /sys/power/state; } 2>/dev/null || sleep "$secs"
}

init
while true; do
  if fetch_and_show; then
    go_to_sleep "$(sleep_secs)"
  else
    go_to_sleep 300   # lỗi thì 5 phút sau thử lại
  fi
done
