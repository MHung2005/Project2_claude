import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, UserCheck, Clock3, UserX, UserPlus, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { PieChart, Pie, Cell } from 'recharts';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { getDailyAnalytics, getStats } from '../services/managerService';
import './ManagerDashboard.css';

const DEPT_COLORS = {
  'Kỹ thuật': '#1f6f3f',
  'Kinh doanh': '#3b82f6',
  'Vận hành': '#dc2626',
  default: '#94a3b8',
};

const PAGE_SIZE = 4;

export default function ManagerDashboard() {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const handler = setTimeout(() => setSearch(searchInput), 350);
    return () => clearTimeout(handler);
  }, [searchInput]);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setErrorMsg('');

    Promise.allSettled([getDailyAnalytics(undefined, search), getStats()])
      .then(([analyticsRes, statsRes]) => {
        if (!isMounted) return;
        if (analyticsRes.status === 'fulfilled') {
          setAnalytics(analyticsRes.value.data?.data);
        }
        if (statsRes.status === 'fulfilled') {
          setStats(statsRes.value.data?.data);
        }
        if (analyticsRes.status === 'rejected' && statsRes.status === 'rejected') {
          setErrorMsg('Không thể tải dữ liệu tổng quan. Vui lòng thử lại sau.');
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [search]);

  useEffect(() => {
    setPage(0);
  }, [search]);

  // analytics shape: { date, total_employees, present, on_time, late, absent, records }
  const records = useMemo(() => {
    const raw = analytics?.records || [];
    return Array.isArray(raw) ? raw : [];
  }, [analytics]);

  const totalRecords = records.length;
  const pageCount = Math.max(1, Math.ceil(totalRecords / PAGE_SIZE));
  const pagedRecords = records.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  // Build department breakdown locally — backend doesn't return this directly
  const deptBreakdown = useMemo(() => {
    const counts = {};
    records.forEach((r) => {
      if (r.status !== 'Vắng mặt') {
        const dept = r.department || 'Khác';
        counts[dept] = (counts[dept] || 0) + 1;
      }
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [records]);

  const totalCount = useMemo(
    () => deptBreakdown.reduce((sum, d) => sum + (d.value || 0), 0),
    [deptBreakdown]
  );

  // stats shape: { today, total, absent, late, on_time, rate }
  const onTimeRate = stats?.rate;
  const checkedIn = analytics?.present ?? stats?.today;
  const lateCount = analytics?.late ?? stats?.late;
  const notCheckedIn = analytics?.absent ?? stats?.absent;
  const totalStaff = analytics?.total_employees ?? stats?.total;

  return (
    <div className="page">
      <TopNav showRoleSwitch />
      <div className="page__body">
        <Sidebar statusLabel="Đang hoạt động" />
        <main className="md">
          <div className="md__header">
            <div>
              <h1 className="md__title">Tổng quan hệ thống</h1>
              <p className="md__subtitle">
                Chào mừng trở lại
                {typeof checkedIn === 'number' ? `, hôm nay có ${checkedIn} nhân sự đã điểm danh.` : '.'}
              </p>
            </div>
            <button className="md__export">
              <Download size={16} strokeWidth={2.2} />
              Xuất báo cáo
            </button>
          </div>

          {errorMsg && <div className="md__alert">{errorMsg}</div>}

          <div className="md__metric-grid">
            <div className="md__metric-card">
              <div className="md__metric-label">TỶ LỆ ĐÚNG GIỜ</div>
              <div className="md__metric-value md__metric-value--accent">
                {typeof onTimeRate === 'number' ? `${Math.round(onTimeRate)}%` : '--'}
              </div>
              <div className="md__progress-track">
                <div
                  className="md__progress-fill"
                  style={{ width: `${typeof onTimeRate === 'number' ? onTimeRate : 0}%` }}
                />
              </div>
            </div>

            <div className="md__metric-card">
              <div className="md__metric-row">
                <div className="md__metric-label">ĐÃ ĐIỂM DANH</div>
                <div className="md__metric-icon md__metric-icon--accent">
                  <UserCheck size={18} strokeWidth={2.2} />
                </div>
              </div>
              <div className="md__metric-value">{checkedIn ?? '--'}</div>
              <div className="md__metric-trend md__metric-trend--up">↗ Cập nhật theo thời gian thực</div>
            </div>

            <div className="md__metric-card">
              <div className="md__metric-row">
                <div className="md__metric-label">ĐI MUỘN</div>
                <div className="md__metric-icon md__metric-icon--danger">
                  <Clock3 size={18} strokeWidth={2.2} />
                </div>
              </div>
              <div className="md__metric-value md__metric-value--danger">{lateCount ?? '--'}</div>
              <div className="md__metric-trend md__metric-trend--down">↘ Cần lưu ý</div>
            </div>

            <div className="md__metric-card">
              <div className="md__metric-row">
                <div className="md__metric-label">CHƯA CHECK-IN</div>
                <div className="md__metric-icon md__metric-icon--muted">
                  <UserX size={18} strokeWidth={2.2} />
                </div>
              </div>
              <div className="md__metric-value">{notCheckedIn ?? '--'}</div>
              <div className="md__metric-trend">
                {typeof totalStaff === 'number' ? `Trên tổng ${totalStaff} nhân sự` : 'Đang cập nhật...'}
              </div>
            </div>
          </div>

          <div className="md__main-grid">
            <div className="md__panel">
              <h2 className="md__panel-title">Điểm danh theo phòng ban</h2>
              {deptBreakdown.length === 0 ? (
                <div className="md__empty">Chưa có dữ liệu phân bổ phòng ban.</div>
              ) : (
                <>
                  <div className="md__donut-wrap">
                    <PieChart width={200} height={200}>
                      <Pie
                        data={deptBreakdown}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={62}
                        outerRadius={94}
                        paddingAngle={2}
                        startAngle={90}
                        endAngle={-270}
                      >
                        {deptBreakdown.map((entry) => (
                          <Cell
                            key={entry.name}
                            fill={DEPT_COLORS[entry.name] || DEPT_COLORS.default}
                          />
                        ))}
                      </Pie>
                    </PieChart>
                    <div className="md__donut-center">
                      <div className="md__donut-total">{totalCount}</div>
                      <div className="md__donut-label">Tổng cộng</div>
                    </div>
                  </div>
                  <ul className="md__legend">
                    {deptBreakdown.map((d) => (
                      <li key={d.name} className="md__legend-item">
                        <span
                          className="md__legend-dot"
                          style={{ background: DEPT_COLORS[d.name] || DEPT_COLORS.default }}
                        />
                        <span className="md__legend-name">{d.name}</span>
                        <span className="md__legend-value">
                          {totalCount ? Math.round((d.value / totalCount) * 100) : 0}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>

            <div className="md__panel md__panel--table">
              <div className="md__table-header">
                <h2 className="md__panel-title">Danh sách điểm danh</h2>
                <div className="md__search">
                  <Search size={16} strokeWidth={2} />
                  <input
                    type="text"
                    placeholder="Tìm nhân viên..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                  />
                </div>
              </div>

              <div className="md__table-scroll">
                <table className="md__table">
                  <thead>
                    <tr>
                      <th>Họ và tên</th>
                      <th>Phòng ban</th>
                      <th>Thời gian</th>
                      <th>Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      Array.from({ length: PAGE_SIZE }).map((_, i) => (
                        <tr key={i}>
                          <td colSpan={4}>
                            <div className="md__skeleton-row" />
                          </td>
                        </tr>
                      ))
                    ) : pagedRecords.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="md__empty-cell">
                          Không tìm thấy nhân viên phù hợp.
                        </td>
                      </tr>
                    ) : (
                      pagedRecords.map((rec, idx) => {
                        const name = rec.name || '—';
                        const dept = rec.department || '—';
                        const time = rec.checkin_time
                          ? new Date(rec.checkin_time.replace(' ', 'T')).toLocaleTimeString('vi-VN', {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })
                          : '--:--:--';
                        const statusRaw = (rec.status || '').toLowerCase();
                        let statusLabel = rec.status || 'Chưa Check-in';
                        let statusClass = 'md__badge--muted';
                        if (statusRaw.includes('muộn')) {
                          statusLabel = 'Đi muộn';
                          statusClass = 'md__badge--danger';
                        } else if (statusRaw.includes('đúng')) {
                          statusLabel = 'Đúng giờ';
                          statusClass = 'md__badge--success';
                        } else if (statusRaw.includes('vắng') || !rec.status) {
                          statusLabel = 'Vắng mặt';
                          statusClass = 'md__badge--muted';
                        }
                        return (
                          <tr key={rec.user_id || idx}>
                            <td>
                              <div className="md__person">
                                <span className="md__avatar" />
                                {name}
                              </div>
                            </td>
                            <td className="md__muted-text">{dept}</td>
                            <td className="md__muted-text">{time}</td>
                            <td>
                              <span className={`md__badge ${statusClass}`}>{statusLabel}</span>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              <div className="md__table-footer">
                <span>
                  Hiển thị {pagedRecords.length} trong {totalRecords} bản ghi
                </span>
                <div className="md__pagination">
                  <button
                    disabled={page === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    aria-label="Trang trước"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    disabled={page >= pageCount - 1}
                    onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                    aria-label="Trang sau"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="md__map-banner">
            <div className="md__map-banner-info">
              <div className="md__map-banner-title">
                <MapPinIcon /> Theo dõi GPS thời gian thực
              </div>
              <p>Tất cả nhân sự đang ở trong vùng an toàn quy định.</p>
            </div>
          </div>

          <button className="md__fab" onClick={() => navigate('/cap-tai-khoan')} aria-label="Cấp tài khoản">
            <UserPlus size={22} strokeWidth={2.2} />
          </button>
        </main>
      </div>
    </div>
  );
}

function MapPinIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 1 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}