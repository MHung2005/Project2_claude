import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock3, PlaneTakeoff, Fingerprint, Map } from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { getProfile, getMonthlyStats, getAttendance } from '../services/employeeService';
import { useAuth } from '../context/AuthContext';
import './EmployeeDashboard.css';

const WEEKDAYS = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];

function greetingForHour(hour) {
  if (hour < 11) return 'Chào buổi sáng';
  if (hour < 13) return 'Chào buổi trưa';
  if (hour < 18) return 'Chào buổi chiều';
  return 'Chào buổi tối';
}

function formatToday() {
  const now = new Date();
  return `Hôm nay là ${WEEKDAYS[now.getDay()]}, ngày ${now.getDate()} tháng ${now.getMonth() + 1}`;
}

function pad(n) {
  return String(n).padStart(2, '0');
}

export default function EmployeeDashboard() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setLoading(true);
      setErrorMsg('');
      try {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;

        const start = new Date(year, month - 1, 1);
        const end = now;
        const start_date = `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}`;
        const end_date = `${end.getFullYear()}-${pad(end.getMonth() + 1)}-${pad(end.getDate())}`;

        const [profileRes, statsRes, attendanceRes] = await Promise.allSettled([
          getProfile(),
          getMonthlyStats(year, month),
          getAttendance(start_date, end_date),
        ]);

        if (!isMounted) return;

        if (profileRes.status === 'fulfilled') {
          const profileData = profileRes.value.data?.data;
          setProfile(profileData);
          if (profileData?.name) {
            setUser((prev) => ({ ...prev, name: profileData.name }));
          }
        }
        if (statsRes.status === 'fulfilled') {
          setStats(statsRes.value.data?.data);
        }
        if (attendanceRes.status === 'fulfilled') {
          const raw = attendanceRes.value.data?.data;
          const list = Array.isArray(raw) ? raw : raw?.records || [];
          setLogs(list.slice(-3).reverse());
        }

        if (
          profileRes.status === 'rejected' &&
          statsRes.status === 'rejected' &&
          attendanceRes.status === 'rejected'
        ) {
          setErrorMsg('Không thể tải dữ liệu bảng điều khiển. Vui lòng thử lại sau.');
        }
      } catch (err) {
        if (isMounted) setErrorMsg('Đã xảy ra lỗi khi tải dữ liệu.');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    load();
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const displayName = profile?.name || user?.name || 'Nhân viên';

  // stats shape from backend: { year, month, total_days, present, on_time, late, absent, records }
  const workedDays = stats?.present ?? '--';
  const totalDays = stats?.total_days ?? '--';
  const lateCount = stats?.late ?? '--';
  const leaveRemaining = stats?.absent ?? '--';

  const progress =
    typeof workedDays === 'number' && typeof totalDays === 'number' && totalDays > 0
      ? Math.min(100, Math.round((workedDays / totalDays) * 100))
      : 0;

  const circleCircumference = 2 * Math.PI * 26;
  const circleOffset = circleCircumference - (progress / 100) * circleCircumference;

  return (
    <div className="page">
      <TopNav showRoleSwitch={user?.role === 'manager'} />
      <div className="page__body">
        <Sidebar />
        <main className="ed">
          <div className="ed__header">
            <h1 className="ed__title">
              {greetingForHour(new Date().getHours())}, {displayName}
            </h1>
            <p className="ed__date">{formatToday()}</p>
          </div>

          {errorMsg && <div className="ed__alert">{errorMsg}</div>}

          <div className="ed__summary-card">
            <div>
              <div className="ed__label">Số ngày công</div>
              <div className="ed__big-number">
                {workedDays}
                {totalDays !== '--' && <span className="ed__big-number-sub"> / {totalDays}</span>}
              </div>
            </div>
            <div className="ed__progress-ring" aria-hidden="true">
              <svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="26" fill="none" stroke="#e6e9ed" strokeWidth="6" />
                <circle
                  cx="32"
                  cy="32"
                  r="26"
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeWidth="6"
                  strokeLinecap="round"
                  strokeDasharray={circleCircumference}
                  strokeDashoffset={circleOffset}
                  transform="rotate(-90 32 32)"
                />
              </svg>
              <div className="ed__progress-icon">📅</div>
            </div>
          </div>

          <div className="ed__stat-grid">
            <div className="ed__stat-card">
              <div className="ed__stat-icon ed__stat-icon--red">
                <Clock3 size={20} strokeWidth={2} />
              </div>
              <div className="ed__stat-label">Đi muộn/Về sớm</div>
              <div className="ed__stat-value ed__stat-value--red">
                {lateCount}
                {lateCount !== '--' ? ' lần' : ''}
              </div>
            </div>
            <div className="ed__stat-card">
              <div className="ed__stat-icon ed__stat-icon--blue">
                <PlaneTakeoff size={20} strokeWidth={2} />
              </div>
              <div className="ed__stat-label">Ngày vắng (tháng này)</div>
              <div className="ed__stat-value ed__stat-value--blue">
                {leaveRemaining}
                {leaveRemaining !== '--' ? ' ngày' : ''}
              </div>
            </div>
          </div>

          <button className="ed__checkin-btn" onClick={() => navigate('/diem-danh')}>
            <Fingerprint size={20} strokeWidth={2} />
            Điểm danh ngay
          </button>

          <div className="ed__activity">
            <div className="ed__activity-header">
              <h2>Hoạt động gần đây</h2>
              <button className="ed__see-all" onClick={() => navigate('/thong-ke')}>
                Xem tất cả
              </button>
            </div>

            {loading ? (
              <div className="ed__skeleton-list">
                {[0, 1, 2].map((i) => (
                  <div className="ed__skeleton-row" key={i} />
                ))}
              </div>
            ) : logs.length === 0 ? (
              <div className="ed__empty">Chưa có dữ liệu chấm công gần đây.</div>
            ) : (
              <ul className="ed__log-list">
                {logs.map((log, idx) => {
                  const hasCheckin = !!log.timestamp;
                  const hasCheckout = !!log.checkout_time;
                  const status = log.status || (log.gps_ok === 'false' ? 'Thất bại' : 'Thành công');
                  const label = hasCheckout ? 'Ra ca' : hasCheckin ? 'Vào ca' : 'Vắng mặt';
                  const location =
                    log.lat && log.lng ? `${log.lat}, ${log.lng}` : 'Không xác định';
                  const time =
                    (hasCheckout ? log.checkout_time : log.timestamp)
                      ? new Date(
                          (hasCheckout ? log.checkout_time : log.timestamp).replace(' ', 'T')
                        ).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
                      : '--:--';
                  return (
                    <li className="ed__log-row" key={idx}>
                      <span className={`ed__log-dot ${idx === 0 ? 'ed__log-dot--active' : ''}`} />
                      <div className="ed__log-content">
                        <div className="ed__log-title">
                          {label} - {status}
                        </div>
                        <div className="ed__log-sub">{location}</div>
                      </div>
                      <div className="ed__log-time">{time}</div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </main>
      </div>

      <button className="ed__fab" onClick={() => navigate('/diem-danh')} aria-label="Mở bản đồ điểm danh">
        <Map size={22} strokeWidth={2} />
      </button>
    </div>
  );
}