import { useEffect, useState } from 'react';
import { Clock, Save, Loader2, CheckCircle2, Info, AlarmClock } from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { getSchedule, setSchedule } from '../services/managerService';
import { useToast } from '../components/Toast';
import './ScheduleConfig.css';

const WORK_DAY_START = 6;   // 06:00 — mốc hiển thị trục timeline
const WORK_DAY_END   = 22;  // 22:00

function timeToMinutes(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  return h * 60 + m;
}


function calcWorkHours(start, end) {
  const diff = timeToMinutes(end) - timeToMinutes(start);
  if (diff <= 0) return '—';
  const h = Math.floor(diff / 60);
  const m = diff % 60;
  return m > 0 ? `${h}g ${m}p` : `${h} giờ`;
}

// Tỉ lệ % trên trục timeline (6:00 → 22:00 = 960 phút)
function toPercent(timeStr) {
  const totalRange = (WORK_DAY_END - WORK_DAY_START) * 60;
  const mins = timeToMinutes(timeStr) - WORK_DAY_START * 60;
  return Math.min(100, Math.max(0, (mins / totalRange) * 100));
}

export default function ScheduleConfig() {
  const { showToast } = useToast();

  const [startTime, setStartTime]     = useState('08:00');
  const [endTime, setEndTime]         = useState('17:00');
  const [loading, setLoading]         = useState(true);
  const [saving, setSaving]           = useState(false);
  const [saved, setSaved]             = useState(false);
  const [errorMsg, setErrorMsg]       = useState('');

  useEffect(() => {
    setLoading(true);
    getSchedule()
      .then(({ data: payload }) => {
        const d = payload?.data;
        if (d) {
          setStartTime(d.start_time || '08:00');
          setEndTime(d.end_time     || '17:00');
        }
      })
      .catch(() => setErrorMsg('Không thể tải lịch làm việc. Vui lòng thử lại.'))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (timeToMinutes(endTime) <= timeToMinutes(startTime)) {
      showToast('Giờ kết thúc phải sau giờ bắt đầu.', 'error');
      return;
    }

    setSaving(true);
    setSaved(false);
    try {
      await setSchedule(startTime, endTime, 0);
      setSaved(true);
      showToast('Cập nhật lịch làm việc thành công!', 'success');
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      const msg = err?.response?.data?.message || 'Lưu cấu hình thất bại.';
      showToast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  // Timeline visual calculations
  const startPct  = toPercent(startTime);
  const endPct    = toPercent(endTime);
  const fillLeft  = startPct;
  const fillWidth = Math.max(0, endPct - startPct);

  const workHours = calcWorkHours(startTime, endTime);

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar statusLabel="Đang hoạt động" />
        <main className="sc">
          {/* Header */}
          <div className="sc__header">
            <div className="sc__header-icon">
              <Clock size={26} strokeWidth={1.8} />
            </div>
            <div>
              <h1 className="sc__title">Cấu hình lịch làm việc</h1>
              <p className="sc__subtitle">
                Đặt giờ vào ca và giờ ra ca cho nhân viên.
              </p>
            </div>
          </div>

          {errorMsg && <div className="sc__alert">{errorMsg}</div>}

          <div className="sc__body">
            {/* LEFT — form */}
            <div className="sc__card">
              <div className="sc__card-title">
                <AlarmClock size={16} strokeWidth={2} />
                Giờ làm việc
              </div>

              <div className="sc__time-row">
                <div className="sc__field">
                  <label className="sc__label">Giờ bắt đầu (vào ca)</label>
                  <div className="sc__input-wrap">
                    <Clock size={15} strokeWidth={2} className="sc__input-icon" />
                    <input
                      className="sc__input"
                      type="time"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  <span className="sc__hint">Nhân viên được yêu cầu có mặt trước hoặc đúng giờ này. Check-in sau mốc này sẽ bị tính là <strong>Đi muộn</strong>.</span>
                </div>

                <div className="sc__field">
                  <label className="sc__label">Giờ kết thúc (ra ca)</label>
                  <div className="sc__input-wrap">
                    <Clock size={15} strokeWidth={2} className="sc__input-icon" />
                    <input
                      className="sc__input"
                      type="time"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  <span className="sc__hint">Thời điểm kết thúc ca làm việc</span>
                </div>
              </div>

              <button
                className="sc__save-btn"
                onClick={handleSave}
                disabled={saving || loading}
                type="button"
              >
                {saving ? (
                  <><Loader2 size={18} className="sc__spin" /> Đang lưu...</>
                ) : saved ? (
                  <><CheckCircle2 size={18} /> Đã lưu!</>
                ) : (
                  <><Save size={18} strokeWidth={2} /> Lưu lịch làm việc</>
                )}
              </button>
            </div>

            {/* RIGHT — preview */}
            <div className="sc__preview-col">
              {/* Timeline */}
              <div className="sc__timeline-card">
                <div className="sc__timeline-header">
                  LỊCH NGÀY LÀM VIỆC &nbsp;·&nbsp; <span>{startTime} – {endTime}</span>
                </div>
                <div className="sc__timeline-body">
                  <div className="sc__timeline-bar-wrap">
                    <div
                      className="sc__timeline-fill"
                      style={{ left: `${fillLeft}%`, width: `${fillWidth}%` }}
                    >
                      <span className="sc__timeline-fill-label">{workHours}</span>
                    </div>
                  </div>
                  <div className="sc__timeline-labels">
                    <span>06:00</span>
                    <span>10:00</span>
                    <span>14:00</span>
                    <span>18:00</span>
                    <span>22:00</span>
                  </div>

                  <div className="sc__timeline-stats">
                    <div className="sc__stat-box">
                      <div className="sc__stat-label">VÀO CA</div>
                      <div className="sc__stat-value sc__stat-value--blue">{startTime}</div>
                    </div>
                    <div className="sc__stat-box">
                      <div className="sc__stat-label">RA CA</div>
                      <div className="sc__stat-value sc__stat-value--blue">{endTime}</div>
                    </div>
                    <div className="sc__stat-box">
                      <div className="sc__stat-label">TỔNG GIỜ</div>
                      <div className="sc__stat-value sc__stat-value--accent">{workHours}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Info */}
              <div className="sc__info-card">
                <div className="sc__info-title">
                  <Info size={15} strokeWidth={2} /> Hướng dẫn
                </div>
                <ul className="sc__info-list">
                  <li>
                    Hệ thống tự động gắn nhãn <strong>Đúng giờ</strong> / <strong>Đi muộn</strong>
                    khi nhân viên check-in, dựa trên giờ vào ca đã cấu hình.
                  </li>
                  <li>
                    Nhân viên check-in đúng hoặc trước giờ vào ca được tính là <strong>Đúng giờ</strong>;
                    sau mốc đó là <strong>Đi muộn</strong>.
                  </li>
                  <li>
                    Thay đổi lịch chỉ áp dụng cho các lần check-in <strong>sau khi lưu</strong>,
                    không ảnh hưởng đến dữ liệu cũ.
                  </li>
                  <li>
                    Giờ vào ca phải sớm hơn giờ ra ca.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}