#!/usr/bin/env python3
"""Vẽ dashboard lịch + todo cho Kindle Paperwhite 11th gen (1236x1648, xám).

Dữ liệu thật (dùng trong GitHub Actions):
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN  (biến môi trường)
    python render.py --out _site/dashboard.png

Xem trước bằng dữ liệu mẫu:
    python render.py --sample sample.json --out preview.png
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- cấu hình
PW, PH = 1236, 1648   # điểm ảnh thật của màn Kindle
# Phóng to toàn bộ bố cục (chữ + khoảng cách). 1.0 = cỡ gốc, 1.3 = to hơn 30%.
SCALE = float(os.environ.get("DASH_SCALE", "1.3"))
W, H = round(PW / SCALE), round(PH / SCALE)   # kích thước "logic" dùng khi bố trí
TZ = ZoneInfo(os.environ.get("DASH_TZ", "Asia/Ho_Chi_Minh"))
# Bỏ qua các lịch có tên trong danh sách này (phân tách bằng dấu phẩy)
SKIP_CALENDARS = {s.strip() for s in os.environ.get("DASH_SKIP_CALENDARS", "").split(",") if s.strip()}

FONT_DIR = Path(__file__).parent / "fonts"
BLACK, DARK, MID, LIGHT, PALE, WHITE = 0, 60, 120, 180, 225, 255
MARGIN = round(72 / SCALE ** 0.5)   # lề tăng ít hơn chữ để không phí chỗ

THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    for p in (FONT_DIR / f"Inter-{weight}.otf",
              Path(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if weight in ('Bold', 'SemiBold') else ''}.ttf")):
        if p.exists():
            return ImageFont.truetype(str(p), round(size * SCALE))
    return ImageFont.load_default(round(size * SCALE))


class ScaledDraw:
    """Vẽ theo toạ độ logic, tự nhân SCALE sang điểm ảnh thật (chữ vẫn nét căng)."""

    def __init__(self, img):
        self._d = ImageDraw.Draw(img)

    @staticmethod
    def _xy(v):
        if isinstance(v, (list, tuple)) and v and isinstance(v[0], (list, tuple)):
            return [(x * SCALE, y * SCALE) for x, y in v]
        return [c * SCALE for c in v]

    @staticmethod
    def _kw(kw):
        for k in ("width", "radius"):
            if k in kw:
                kw[k] = max(1, round(kw[k] * SCALE))
        return kw

    def textlength(self, text, font):
        return self._d.textlength(text, font=font) / SCALE

    def text(self, xy, text, **kw):
        self._d.text((xy[0] * SCALE, xy[1] * SCALE), text, **kw)

    def line(self, xy, **kw):
        self._d.line(self._xy(xy), **self._kw(kw))

    def polygon(self, xy, **kw):
        self._d.polygon(self._xy(xy), **self._kw(kw))

    def ellipse(self, xy, **kw):
        self._d.ellipse(self._xy(xy), **self._kw(kw))

    def rounded_rectangle(self, xy, **kw):
        self._d.rounded_rectangle(self._xy(xy), **self._kw(kw))


# ---------------------------------------------------------------- dữ liệu
@dataclass
class Event:
    title: str
    start: datetime | None  # None = cả ngày
    end: datetime | None
    location: str = ""
    calendar: str = ""

    @property
    def all_day(self) -> bool:
        return self.start is None


@dataclass
class Task:
    title: str
    due: date | None
    list_name: str = ""
    notes: str = ""


def _google_session():
    import requests

    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return s


def _get_all(s, url, params=None):
    params = dict(params or {})
    while True:
        r = s.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        yield from data.get("items", [])
        if not data.get("nextPageToken"):
            return
        params["pageToken"] = data["nextPageToken"]


def fetch_google(today: date) -> tuple[list[Event], list[Task]]:
    s = _google_session()
    t0 = datetime.combine(today, time.min, TZ)
    t1 = t0 + timedelta(days=2)

    events: list[Event] = []
    for cal in _get_all(s, "https://www.googleapis.com/calendar/v3/users/me/calendarList"):
        name = cal.get("summaryOverride") or cal.get("summary", "")
        if name in SKIP_CALENDARS or cal.get("selected") is False:
            continue
        for e in _get_all(s, f"https://www.googleapis.com/calendar/v3/calendars/{cal['id']}/events", {
            "timeMin": t0.isoformat(), "timeMax": t1.isoformat(),
            "singleEvents": "true", "orderBy": "startTime", "maxResults": 100,
        }):
            if e.get("status") == "cancelled":
                continue
            if any(a.get("self") and a.get("responseStatus") == "declined" for a in e.get("attendees", [])):
                continue
            st, en = e.get("start", {}), e.get("end", {})
            if "dateTime" in st:
                start = datetime.fromisoformat(st["dateTime"]).astimezone(TZ)
                end = datetime.fromisoformat(en["dateTime"]).astimezone(TZ)
                events.append(Event(e.get("summary", "(Không tiêu đề)"), start, end, e.get("location", ""), name))
            else:
                d0, d1 = date.fromisoformat(st["date"]), date.fromisoformat(en["date"])
                # mỗi ngày của sự kiện cả ngày -> ghi lại ngày bắt đầu bằng end=None, start=None
                for i in range((d1 - d0).days):
                    d = d0 + timedelta(days=i)
                    if today <= d <= today + timedelta(days=1):
                        ev = Event(e.get("summary", "(Không tiêu đề)"), None, None, e.get("location", ""), name)
                        ev.__dict__["day"] = d
                        events.append(ev)

    tasks: list[Task] = []
    for tl in _get_all(s, "https://tasks.googleapis.com/tasks/v1/users/@me/lists"):
        for t in _get_all(s, f"https://tasks.googleapis.com/tasks/v1/lists/{tl['id']}/tasks", {
            "showCompleted": "false", "showHidden": "false", "maxResults": 100,
        }):
            if not t.get("title", "").strip():
                continue
            due = date.fromisoformat(t["due"][:10]) if t.get("due") else None
            tasks.append(Task(t["title"].strip(), due, tl.get("title", ""), t.get("notes", "")))
    return events, tasks


def parse_payload(data: dict, today: date) -> tuple[list[Event], list[Task]]:
    """Đọc JSON từ Google Apps Script (apps_script.gs)."""
    events: list[Event] = []
    for e in data.get("events", []):
        name = e.get("calendar", "")
        if name in SKIP_CALENDARS:
            continue
        if e.get("allDay"):
            d0 = date.fromisoformat(e["startDate"])
            d1 = date.fromisoformat(e.get("endDate") or e["startDate"])
            if d1 <= d0:
                d1 = d0 + timedelta(days=1)
            d = d0
            while d < d1:
                if today <= d <= today + timedelta(days=1):
                    ev = Event(e["title"], None, None, e.get("location", ""), name)
                    ev.__dict__["day"] = d
                    events.append(ev)
                d += timedelta(days=1)
        else:
            start = datetime.fromisoformat(e["start"].replace("Z", "+00:00")).astimezone(TZ)
            end = datetime.fromisoformat(e["end"].replace("Z", "+00:00")).astimezone(TZ)
            events.append(Event(e["title"], start, end, e.get("location", ""), name))
    tasks = [Task(t["title"], date.fromisoformat(t["due"]) if t.get("due") else None,
                  t.get("list", ""), t.get("notes", "")) for t in data.get("tasks", [])]
    return events, tasks


def fetch_appscript(url: str, today: date) -> tuple[list[Event], list[Task]]:
    import requests

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise SystemExit(f"Apps Script báo lỗi: {data['error']} (kiểm tra token trong DATA_URL)")
    global CLAUDE_USAGE
    CLAUDE_USAGE = data.get("claude")
    return parse_payload(data, today)


# ---------------------------------------------------------------- mức dùng Claude
CLAUDE_USAGE: dict | None = None   # {"five_hour": {"utilization", "resets_at"}, "seven_day": {...}, "fetched_at"}
THU_NGAN = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _reset_label(iso: str | None, now: datetime) -> str:
    if not iso:
        return ""
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return ""
    if t.date() == now.date():
        return f"đặt lại {t:%H:%M}"
    return f"đặt lại {THU_NGAN[t.weekday()]} {t:%H:%M}"


def draw_claude(d, y: int, usage: dict, now: datetime) -> int:
    """Hai thanh: phiên 5 giờ + giới hạn tuần. Trả về y mới."""
    f_lab, f_pct, f_small = font("Bold", 24), font("Bold", 30), font("Regular", 22)
    d.text((MARGIN, y), "CLAUDE", font=f_lab, fill=BLACK)
    fetched = usage.get("fetched_at")
    if fetched:
        try:
            ft = datetime.fromisoformat(fetched.replace("Z", "+00:00")).astimezone(TZ)
            age = (now - ft).total_seconds() / 3600
            if age > 2:
                note = f"số liệu cũ, lúc {ft:%H:%M %d/%m}"
                d.text((W - MARGIN - d.textlength(note, font=f_small), y + 2), note, font=f_small, fill=MID)
        except ValueError:
            pass
    y += 38
    gap = 40
    col_w = (W - 2 * MARGIN - gap) / 2
    for i, (key, name) in enumerate((("five_hour", "Phiên hiện tại"), ("seven_day", "Tuần này"))):
        x0 = MARGIN + i * (col_w + gap)
        v = (usage.get(key) or {})
        pct = v.get("utilization")
        pct_txt = "--" if pct is None else f"{round(pct)}%"
        d.text((x0, y), name, font=font("Medium", 24), fill=DARK)
        d.text((x0 + col_w - d.textlength(pct_txt, font=f_pct), y - 4), pct_txt, font=f_pct, fill=BLACK)
        by = y + 38
        d.rounded_rectangle([x0, by, x0 + col_w, by + 16], radius=8, outline=BLACK, width=2)
        if pct:
            fill_w = max(16, col_w * min(pct, 100) / 100)
            d.rounded_rectangle([x0, by, x0 + fill_w, by + 16], radius=8, fill=BLACK)
        d.text((x0, by + 24), _reset_label(v.get("resets_at"), now), font=f_small, fill=MID)
    return y + 92


def load_sample(path: str, today: date) -> tuple[list[Event], list[Task]]:
    """Mẫu JSON: giờ dạng "HH:MM" tính theo hôm nay, "+1 HH:MM" là ngày mai; due là số ngày lệch."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    def parse(v):
        off = 0
        if v.startswith("+"):
            o, v = v.split(" ", 1)
            off = int(o)
        hh, mm = map(int, v.split(":"))
        return datetime.combine(today + timedelta(days=off), time(hh, mm), TZ)

    events = []
    for e in data.get("events", []):
        if "day" in e:
            ev = Event(e["title"], None, None, e.get("location", ""))
            ev.__dict__["day"] = today + timedelta(days=e["day"])
        else:
            ev = Event(e["title"], parse(e["start"]), parse(e["end"]), e.get("location", ""))
        events.append(ev)
    tasks = [Task(t["title"], today + timedelta(days=t["due"]) if t.get("due") is not None else None,
                  t.get("list", "")) for t in data.get("tasks", [])]
    return events, tasks


def event_day(e: Event) -> date:
    return e.__dict__.get("day") if e.all_day else e.start.date()


# ---------------------------------------------------------------- vẽ
def fit(d: ImageDraw.ImageDraw, text: str, f, max_w: int) -> str:
    if d.textlength(text, font=f) <= max_w:
        return text
    while text and d.textlength(text + "…", font=f) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def wrap(d, text, f, max_w, max_lines=2):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit(d, lines[-1] + " …", f, max_w)
    return [fit(d, l, f, max_w) for l in lines]


# ---------------------------------------------------------------- thời tiết
LAT = float(os.environ.get("DASH_LAT", "12.2388"))   # mặc định: Nha Trang
LON = float(os.environ.get("DASH_LON", "109.1967"))

WMO = {0: ("Trời quang", "sun"), 1: ("Nắng nhẹ", "sun"), 2: ("Có mây", "partly"), 3: ("Nhiều mây", "cloud"),
       45: ("Sương mù", "fog"), 48: ("Sương mù", "fog"), 51: ("Mưa phùn", "rain"), 53: ("Mưa phùn", "rain"),
       55: ("Mưa phùn", "rain"), 61: ("Mưa nhỏ", "rain"), 63: ("Mưa vừa", "rain"), 65: ("Mưa to", "rain"),
       80: ("Mưa rào", "rain"), 81: ("Mưa rào", "rain"), 82: ("Mưa rất to", "rain"),
       95: ("Dông", "storm"), 96: ("Dông, mưa đá", "storm"), 99: ("Dông, mưa đá", "storm")}


@dataclass
class Weather:
    temp: float
    code: int
    tmin: float
    tmax: float
    rain: int            # % khả năng mưa
    aqi: int | None = None

    @property
    def desc(self):
        return WMO.get(self.code, ("", "cloud"))[0]

    @property
    def icon(self):
        return WMO.get(self.code, ("", "cloud"))[1]


def fetch_weather() -> Weather | None:
    import requests
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": LAT, "longitude": LON, "timezone": str(TZ), "forecast_days": 1,
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        }, timeout=20).json()
        w = Weather(r["current"]["temperature_2m"], r["current"]["weather_code"],
                    r["daily"]["temperature_2m_min"][0], r["daily"]["temperature_2m_max"][0],
                    r["daily"]["precipitation_probability_max"][0] or 0)
    except Exception as e:  # thời tiết lỗi thì vẫn vẽ phần còn lại
        print("Không lấy được thời tiết:", e)
        return None
    try:
        a = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params={
            "latitude": LAT, "longitude": LON, "current": "us_aqi"}, timeout=20).json()
        w.aqi = round(a["current"]["us_aqi"])
    except Exception:
        pass
    return w


def aqi_label(v):
    for lim, name in ((50, "Tốt"), (100, "Trung bình"), (150, "Kém"), (200, "Xấu"), (300, "Rất xấu")):
        if v <= lim:
            return name
    return "Nguy hại"


def draw_icon(d, kind, cx, cy, s):
    """Icon thời tiết đơn giản, nét đen, hợp e-ink. s = bán kính cơ sở."""
    import math

    def sun(x, y, r):
        d.ellipse([x - r, y - r, x + r, y + r], outline=BLACK, width=6)
        for i in range(8):
            a = i * math.pi / 4
            d.line([(x + math.cos(a) * r * 1.45, y + math.sin(a) * r * 1.45),
                    (x + math.cos(a) * r * 1.9, y + math.sin(a) * r * 1.9)], fill=BLACK, width=6)

    def cloud(x, y, w, fill=WHITE):
        h = w * 0.55
        parts = [(x - w * .30, y + h * .05, w * .28), (x + w * .02, y - h * .25, w * .34), (x + w * .32, y + h * .08, w * .24)]
        for px, py, r in parts:  # viền
            d.ellipse([px - r - 6, py - r - 6, px + r + 6, py + r + 6], fill=BLACK)
        d.rounded_rectangle([x - w * .58 - 6, y - 6, x + w * .56 + 6, y + h * .45 + 6], radius=int(h * .3), fill=BLACK)
        for px, py, r in parts:
            d.ellipse([px - r, py - r, px + r, py + r], fill=fill)
        d.rounded_rectangle([x - w * .58, y, x + w * .56, y + h * .45], radius=int(h * .3), fill=fill)

    if kind == "sun":
        sun(cx, cy, s * .55)
    elif kind == "partly":
        sun(cx + s * .35, cy - s * .35, s * .42)
        cloud(cx - s * .1, cy + s * .1, s * 1.5)
    elif kind in ("cloud", "fog"):
        cloud(cx, cy - s * .1, s * 1.7)
        if kind == "fog":
            for i in range(3):
                d.line([(cx - s * .8, cy + s * .55 + i * 16), (cx + s * .8, cy + s * .55 + i * 16)], fill=BLACK, width=6)
    else:  # rain / storm
        cloud(cx, cy - s * .3, s * 1.7)
        if kind == "storm":
            d.polygon([(cx, cy + s * .25), (cx - s * .25, cy + s * .75), (cx, cy + s * .7),
                       (cx - s * .15, cy + s * 1.1), (cx + s * .3, cy + s * .55), (cx + s * .05, cy + s * .58)], fill=BLACK)
        else:
            for i in (-1, 0, 1):
                x = cx + i * s * .45
                d.line([(x + 8, cy + s * .35), (x - 8, cy + s * .8)], fill=BLACK, width=7)


# ---------------------------------------------------------------- vẽ
def section_title(d, y, text, right=""):
    f = font("Bold", 28)
    d.text((MARGIN, y), text.upper(), font=f, fill=BLACK)
    if right:
        fr = font("Medium", 26)
        d.text((W - MARGIN - d.textlength(right, font=fr), y + 2), right, font=fr, fill=MID)
    d.line([(MARGIN, y + 44), (W - MARGIN, y + 44)], fill=BLACK, width=3)
    return y + 62


def hm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def due_tag(t: Task, today: date):
    if not t.due:
        return ""
    if t.due < today:
        return "Quá hạn"
    if t.due == today:
        return "Hôm nay"
    if t.due == today + timedelta(days=1):
        return "Ngày mai"
    return f"{t.due.day}/{t.due.month}"


def render(events: list[Event], tasks: list[Task], now: datetime, weather: Weather | None = None) -> Image.Image:
    from lunar import solar_to_lunar, year_name

    today, tomorrow = now.date(), now.date() + timedelta(days=1)
    img = Image.new("L", (PW, PH), WHITE)
    d = ScaledDraw(img)
    f_sub = font("Regular", 28)

    # ============ HEADER: ngày + âm lịch | thời tiết
    y = 56
    d.text((MARGIN, y), THU[today.weekday()], font=font("Bold", 88), fill=BLACK)
    d.text((MARGIN, y + 112), f"{today.day} tháng {today.month}, {today.year}", font=font("SemiBold", 38), fill=DARK)
    ld, lm, ly, leap = solar_to_lunar(today.day, today.month, today.year)
    lunar_txt = f"Âm lịch {ld}/{lm}{' nhuận' if leap else ''} · năm {year_name(ly)}"
    d.text((MARGIN, y + 164), lunar_txt, font=f_sub, fill=MID)

    if weather:
        right = W - MARGIN
        ft = font("Bold", 96)
        t = f"{round(weather.temp)}°"
        tw = d.textlength(t, font=ft)
        d.text((right - tw, y - 6), t, font=ft, fill=BLACK)
        draw_icon(d, weather.icon, int(right - tw - 85), y + 52, 62)
        l1 = f"{weather.desc} · {round(weather.tmin)}–{round(weather.tmax)}°"
        l2 = f"Mưa {weather.rain}%" + (f" · AQI {weather.aqi} {aqi_label(weather.aqi)}" if weather.aqi is not None else "")
        fw = font("Medium", 28)
        d.text((right - d.textlength(l1, font=fw), y + 124), l1, font=fw, fill=DARK)
        d.text((right - d.textlength(l2, font=f_sub), y + 164), l2, font=f_sub, fill=MID)
    y += 222
    d.line([(MARGIN, y), (W - MARGIN, y)], fill=BLACK, width=6)
    y += 32

    # ============ MỨC DÙNG CLAUDE (nếu Mac mini có gửi số liệu)
    if CLAUDE_USAGE:
        y = draw_claude(d, y, CLAUDE_USAGE, now)
        d.line([(MARGIN, y), (W - MARGIN, y)], fill=PALE, width=2)
        y += 28

    ev_today = sorted([e for e in events if event_day(e) == today], key=lambda e: (not e.all_day, e.start or now))
    ev_tom = sorted([e for e in events if event_day(e) == tomorrow], key=lambda e: (not e.all_day, e.start or now))
    timed = [e for e in ev_today if not e.all_day]
    nxt = next((e for e in timed if e.end > now), None)

    # ============ THẺ "TIẾP THEO" (nền đen, nổi bật trên e-ink)
    if nxt:
        live = nxt.start <= now
        has_loc = bool(nxt.location)
        ch = 150 if has_loc else 118
        d.rounded_rectangle([MARGIN, y, W - MARGIN, y + ch], radius=18, fill=BLACK)
        label = ("ĐANG DIỄN RA" if live else "TIẾP THEO") + f" · {hm(nxt.start)}–{hm(nxt.end)}"
        d.text((MARGIN + 32, y + 18), label, font=font("SemiBold", 26), fill=PALE)
        d.text((MARGIN + 32, y + 52), fit(d, nxt.title, font("Bold", 44), W - 2 * MARGIN - 64),
               font=font("Bold", 44), fill=WHITE)
        if has_loc:
            d.text((MARGIN + 32, y + 106), fit(d, "@ " + nxt.location, f_sub, W - 2 * MARGIN - 64), font=f_sub, fill=PALE)
        y += ch + 34

    # ---- tính trước khối dưới cùng (lịch hôm nay + ngày mai) để todo lấp phần giữa
    footer_y = H - 64
    min_todo = 62 + 3 * 72 if tasks else 140   # luôn chừa chỗ cho ít nhất ~3 việc
    cal_max, tom_max = 6, 3

    def _bottom_h(cm, tm):
        cr = min(len(ev_today), cm) or 1
        tr = min(len(ev_tom), tm) or 1
        return (62 + 46 * cr + (36 if len(ev_today) > cm else 0) + 26) + (62 + 44 * tr) + 16

    # thiếu chỗ cho todo → bớt dòng lịch (ngày mai trước, rồi hôm nay)
    while footer_y - _bottom_h(cal_max, tom_max) - y < min_todo and (tom_max > 1 or cal_max > 2):
        if tom_max > 1:
            tom_max -= 1
        else:
            cal_max -= 1
    bottom_y = footer_y - _bottom_h(cal_max, tom_max)

    # ============ VIỆC CẦN LÀM (khu vực chính)
    tasks_open = sorted(tasks, key=lambda t: (t.due is None, t.due or date.max, t.title.lower()))
    overdue = sum(1 for t in tasks_open if t.due and t.due < today)
    due_today = sum(1 for t in tasks_open if t.due == today)
    right = f"{len(tasks_open)} việc" + (f" · {overdue} quá hạn" if overdue else "") + \
        (f" · {due_today} hôm nay" if due_today else "")
    y = section_title(d, y, "Việc cần làm", right if tasks_open else "")
    f_task, box = font("Medium", 32), 36   # mỗi việc đúng 1 dòng, dài thì cắt "…"
    if not tasks_open:
        d.text((MARGIN, y + 6), "Không còn việc nào. Tuyệt vời!", font=font("Regular", 36), fill=MID)
        y += 70
    for i, t in enumerate(tasks_open):
        tag = due_tag(t, today)
        f_tag = font("SemiBold", 22)
        tag_w = int(d.textlength(tag, font=f_tag)) + 28 if tag else 0
        text_w = W - 2 * MARGIN - box - 24 - (tag_w + 20 if tag else 0)
        line = fit(d, t.title, f_task, text_w)
        limit = bottom_y - (16 if i == len(tasks_open) - 1 else 44)  # chừa chỗ cho "+ N việc nữa"
        row_h = 66
        if y + row_h > limit:
            d.text((MARGIN, y + 4), f"+ {len(tasks_open) - i} việc nữa", font=f_sub, fill=MID)
            y += 44
            break
        d.rounded_rectangle([MARGIN, y + 4, MARGIN + box, y + 4 + box], radius=8, outline=BLACK, width=4)
        d.text((MARGIN + box + 24, y + 22), line, font=f_task, fill=BLACK, anchor="lm")
        if tag:
            x1, x0 = W - MARGIN, W - MARGIN - tag_w
            if tag in ("Quá hạn", "Hôm nay"):
                d.rounded_rectangle([x0, y + 4, x1, y + 40], radius=18, fill=BLACK)
                d.text(((x0 + x1) / 2, y + 22), tag, font=f_tag, fill=WHITE, anchor="mm")
            else:
                d.rounded_rectangle([x0, y + 4, x1, y + 40], radius=18, outline=MID, width=2)
                d.text(((x0 + x1) / 2, y + 22), tag, font=f_tag, fill=DARK, anchor="mm")
        y += row_h
        d.line([(MARGIN + box + 28, y - 8), (W - MARGIN, y - 8)], fill=PALE, width=2)
        y += 6

    # ============ LỊCH HÔM NAY (gọn, ghim phía dưới)
    y = bottom_y
    y = section_title(d, y, "Lịch hôm nay", f"{len(ev_today)} sự kiện" if ev_today else "")
    time_w = 250
    f_ev, f_evb = font("Regular", 32), font("SemiBold", 32)
    if not ev_today:
        d.text((MARGIN, y), "Không có sự kiện nào.", font=f_ev, fill=MID)
        y += 46
    shown = list(ev_today)
    while len(shown) > cal_max:   # thiếu chỗ: bỏ sự kiện đã qua trước, rồi tới cuối danh sách
        past_i = next((k for k, x in enumerate(shown) if not x.all_day and x.end <= now), None)
        shown.pop(past_i if past_i is not None else -1)
    for i, e in enumerate(shown):
        past = (not e.all_day) and e.end <= now
        is_next = e is nxt
        col = LIGHT if past else BLACK
        tf = f_evb if is_next else f_ev
        when = "Cả ngày" if e.all_day else f"{hm(e.start)}–{hm(e.end)}"
        d.text((MARGIN, y), when, font=font("Medium", 28), fill=LIGHT if past else DARK)
        d.text((MARGIN + time_w, y - 2), fit(d, e.title, tf, W - 2 * MARGIN - time_w), font=tf, fill=col)
        if past:  # gạch ngang sự kiện đã qua
            tw = min(d.textlength(fit(d, e.title, tf, W - 2 * MARGIN - time_w), font=tf), W - 2 * MARGIN - time_w)
            d.line([(MARGIN + time_w, y + 20), (MARGIN + time_w + tw, y + 20)], fill=LIGHT, width=2)
        y += 46
    if len(ev_today) > len(shown):
        d.text((MARGIN, y), f"+ {len(ev_today) - len(shown)} sự kiện khác", font=f_sub, fill=MID)
        y += 36
    y += 26

    # ============ NGÀY MAI
    y = section_title(d, y, "Ngày mai · " + THU[tomorrow.weekday()],
                      f"{len(ev_tom)} sự kiện" if len(ev_tom) > tom_max else "")
    if not ev_tom:
        d.text((MARGIN, y), "Chưa có lịch.", font=f_ev, fill=MID)
    for e in ev_tom[:tom_max]:
        d.text((MARGIN, y), "Cả ngày" if e.all_day else hm(e.start), font=font("Medium", 28), fill=DARK)
        d.text((MARGIN + time_w, y - 2), fit(d, e.title, f_ev, W - 2 * MARGIN - time_w), font=f_ev, fill=DARK)
        y += 44

    # ============ FOOTER
    d.line([(MARGIN, footer_y), (W - MARGIN, footer_y)], fill=LIGHT, width=2)
    d.text((MARGIN, footer_y + 16), f"Cập nhật {now.strftime('%H:%M %d/%m')}", font=font("Regular", 24), fill=MID)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_site/dashboard.png")
    ap.add_argument("--sample", help="file JSON dữ liệu mẫu (không gọi Google)")
    ap.add_argument("--now", help="giả lập thời điểm, vd 2026-11-03T10:30")
    args = ap.parse_args()

    now = datetime.fromisoformat(args.now).replace(tzinfo=TZ) if args.now else datetime.now(TZ)
    if args.sample:
        events, tasks = load_sample(args.sample, now.date())
        sample = json.loads(Path(args.sample).read_text(encoding="utf-8"))
        w = sample.get("weather")
        weather = Weather(**w) if w else None
        global CLAUDE_USAGE
        CLAUDE_USAGE = sample.get("claude")
    else:
        if os.environ.get("DATA_URL"):
            events, tasks = fetch_appscript(os.environ["DATA_URL"], now.date())
        else:
            events, tasks = fetch_google(now.date())
        weather = fetch_weather()
    img = render(events, tasks, now, weather)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    print(f"Đã lưu {out} ({len(events)} sự kiện, {len(tasks)} việc, thời tiết: {'có' if weather else 'không'})")


if __name__ == "__main__":
    main()
