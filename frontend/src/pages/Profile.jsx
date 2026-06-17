import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  IdCard, Building2, Briefcase, Mail, Phone,
  ScanFace, CalendarClock, CheckCircle2, AlertTriangle, Lock,
} from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { getProfile } from '../services/employeeService';
import { useAuth } from '../context/AuthContext';
import './Profile.css';

function formatDate(dateStr) {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split('-');
  if (!y || !m || !d) return dateStr;
  return `${d}/${m}/${y}`;
}

export default function Profile() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setErrorMsg('');

    getProfile()
      .then(({ data: payload }) => {
        if (!isMounted) return;
        // Backend: { success, message, data: { user_id, name, department, position, email, phone, biometric_status, last_attendance } }
        const data = payload?.data;
        setProfile(data);
        if (data?.name) {
          setUser((prev) => ({ ...prev, name: data.name }));
        }
      })
      .catch(() => {
        if (isMounted) setErrorMsg('Không thể tải hồ sơ cá nhân. Vui lòng thử lại sau.');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const displayName = profile?.name || user?.name || 'Nhân viên';
  const initials = displayName
    .trim()
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(-2)
    .join('')
    .toUpperCase();

  const isFaceRegistered = profile?.biometric_status === 'approved';
  const lastAttendance = formatDate(profile?.last_attendance);

  const infoFields = [
    { icon: IdCard,    label: 'Mã nhân viên',    value: profile?.user_id },
    { icon: Building2, label: 'Phòng ban',       value: profile?.department },
    { icon: Briefcase, label: 'Chức vụ',         value: profile?.position },
    { icon: Mail,      label: 'Email',           value: profile?.email },
    { icon: Phone,     label: 'Số điện thoại',   value: profile?.phone },
  ];

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar />
        <main className="pf">
          <div className="pf__header">
            <h1 className="pf__title">Hồ sơ cá nhân</h1>
            <p className="pf__subtitle">Thông tin tài khoản và trạng thái xác thực của bạn.</p>
          </div>

          {errorMsg && <div className="pf__alert">{errorMsg}</div>}

          {loading ? (
            <div className="pf__skeleton-card" />
          ) : (
            <>
              <div className="pf__profile-card">
                <div className="pf__avatar">{initials || 'NV'}</div>
                <div className="pf__profile-main">
                  <div className="pf__name">{displayName}</div>
                  <div className="pf__role-line">
                    {profile?.position || 'Chưa cập nhật chức vụ'}
                    {profile?.department ? ` · ${profile.department}` : ''}
                  </div>
                </div>
                <div className={`pf__biometric-badge ${isFaceRegistered ? 'pf__biometric-badge--ok' : 'pf__biometric-badge--warn'}`}>
                  {isFaceRegistered
                    ? <CheckCircle2 size={15} strokeWidth={2.2} />
                    : <AlertTriangle size={15} strokeWidth={2.2} />}
                  {isFaceRegistered ? 'Đã đăng ký khuôn mặt' : 'Chưa đăng ký khuôn mặt'}
                </div>
              </div>

              <div className="pf__grid">
                <div className="pf__card">
                  <h2 className="pf__card-title">Thông tin chi tiết</h2>
                  <ul className="pf__field-list">
                    {infoFields.map(({ icon: Icon, label, value }) => (
                      <li className="pf__field-row" key={label}>
                        <div className="pf__field-icon"><Icon size={16} strokeWidth={2} /></div>
                        <div className="pf__field-text">
                          <div className="pf__field-label">{label}</div>
                          <div className="pf__field-value">{value || 'Chưa cập nhật'}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pf__card pf__card--side">
                  <h2 className="pf__card-title">Trạng thái</h2>

                  <div className="pf__status-row">
                    <div className="pf__field-icon"><ScanFace size={16} strokeWidth={2} /></div>
                    <div className="pf__field-text">
                      <div className="pf__field-label">Xác thực khuôn mặt</div>
                      <div className={`pf__field-value ${isFaceRegistered ? 'pf__field-value--accent' : 'pf__field-value--danger'}`}>
                        {isFaceRegistered ? 'Đã kích hoạt' : 'Chưa kích hoạt'}
                      </div>
                    </div>
                  </div>

                  <div className="pf__status-row">
                    <div className="pf__field-icon"><CalendarClock size={16} strokeWidth={2} /></div>
                    <div className="pf__field-text">
                      <div className="pf__field-label">Lần chấm công gần nhất</div>
                      <div className="pf__field-value">{lastAttendance || 'Chưa có dữ liệu'}</div>
                    </div>
                  </div>

                  <div className="pf__actions">
                    {!isFaceRegistered && (
                      <button
                        type="button"
                        className="pf__action-btn pf__action-btn--primary"
                        onClick={() => navigate('/dang-ky-khuon-mat')}
                      >
                        <ScanFace size={16} strokeWidth={2.2} /> Đăng ký khuôn mặt
                      </button>
                    )}
                    <button
                      type="button"
                      className="pf__action-btn"
                      onClick={() => navigate('/doi-mat-khau')}
                    >
                      <Lock size={16} strokeWidth={2.2} /> Đổi mật khẩu
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}