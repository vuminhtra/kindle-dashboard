#!/bin/bash
# Cài job lấy mức dùng Claude trên Mac mini: chạy 10 phút/lần bằng launchd.
# Cách dùng:  bash install.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$DIR/claude_usage.sh"

if [ ! -s "$HOME/.kindle-dashboard-url" ]; then
  echo "Dán DATA_URL (link Web app Apps Script + ?token=...) rồi Enter:"
  read -r url
  printf '%s' "$url" > "$HOME/.kindle-dashboard-url"
  chmod 600 "$HOME/.kindle-dashboard-url"
fi

PLIST="$HOME/Library/LaunchAgents/com.trabo.claude-usage.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.trabo.claude-usage</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$DIR/claude_usage.sh</string></array>
  <key>StartInterval</key><integer>600</integer>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Đã cài. Chạy thử ngay:"
bash "$DIR/claude_usage.sh" || true
tail -n 3 "$DIR/claude_usage.log"
echo
echo "Nếu macOS hỏi 'security muốn truy cập Keychain' → bấm Always Allow (Luôn cho phép)."
