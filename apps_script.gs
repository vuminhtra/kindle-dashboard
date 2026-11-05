/**
 * Google Apps Script: trả về lịch (hôm nay + ngày mai) và việc chưa xong trong Google Tasks dạng JSON.
 * Chạy dưới tài khoản Google của bạn (vuminhtra@gmail.com) — không cần Google Cloud Console.
 *
 * Cài đặt (xem README, mục 1):
 *  1. script.google.com → New project → dán toàn bộ file này.
 *  2. Đổi TOKEN bên dưới thành một chuỗi bí mật bất kỳ.
 *  3. Services (+) → thêm "Google Tasks API".
 *  4. Deploy → New deployment → Web app; Execute as: Me; Who has access: Anyone → Deploy, cho phép quyền.
 *  5. Copy "Web app URL" → GitHub secret DATA_URL = <URL>?token=<TOKEN>
 */
const TOKEN = 'DOI-THANH-CHUOI-BI-MAT';
const TZ = 'Asia/Ho_Chi_Minh';

function doGet(e) {
  if (!e || !e.parameter || e.parameter.token !== TOKEN) {
    return ContentService.createTextOutput('{"error":"forbidden"}').setMimeType(ContentService.MimeType.JSON);
  }
  return ContentService.createTextOutput(JSON.stringify(collect_())).setMimeType(ContentService.MimeType.JSON);
}

function collect_() {
  const today = Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd');
  const start = new Date(today + 'T00:00:00+07:00');
  const end = new Date(start.getTime() + 2 * 86400000);

  const events = [];
  CalendarApp.getAllCalendars().forEach(function (cal) {
    if (cal.isHidden() || !cal.isSelected()) return;
    cal.getEvents(start, end).forEach(function (ev) {
      try {
        if (ev.getMyStatus() === CalendarApp.GuestStatus.NO) return;  // đã từ chối
      } catch (err) {}
      const o = { title: ev.getTitle() || '(Không tiêu đề)', location: ev.getLocation() || '', calendar: cal.getName() };
      if (ev.isAllDayEvent()) {
        o.allDay = true;
        o.startDate = Utilities.formatDate(ev.getAllDayStartDate(), TZ, 'yyyy-MM-dd');
        o.endDate = Utilities.formatDate(ev.getAllDayEndDate(), TZ, 'yyyy-MM-dd');
      } else {
        o.allDay = false;
        o.start = ev.getStartTime().toISOString();
        o.end = ev.getEndTime().toISOString();
      }
      events.push(o);
    });
  });

  const tasks = [];
  const lists = Tasks.Tasklists.list({ maxResults: 100 }).items || [];
  lists.forEach(function (tl) {
    let pageToken;
    do {
      const r = Tasks.Tasks.list(tl.id, { showCompleted: false, showHidden: false, maxResults: 100, pageToken: pageToken });
      (r.items || []).forEach(function (t) {
        if (t.title && t.title.trim()) {
          tasks.push({ title: t.title.trim(), due: t.due ? t.due.slice(0, 10) : null, list: tl.title, notes: t.notes || '' });
        }
      });
      pageToken = r.nextPageToken;
    } while (pageToken);
  });

  return { generated: new Date().toISOString(), events: events, tasks: tasks };
}

/** Bấm Run hàm này trong trình soạn thảo để kiểm tra (xem kết quả ở Execution log). */
function testCollect() {
  Logger.log(JSON.stringify(collect_(), null, 2));
}
