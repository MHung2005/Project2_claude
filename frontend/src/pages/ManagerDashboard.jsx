import { useEffect, useMemo, useState } from 'react';
import { Download, UserCheck, Clock3, UserX, ChevronLeft, ChevronRight, Search, Calendar } from 'lucide-react';
import { PieChart, Pie, Cell } from 'recharts';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { getDailyAnalytics, getStats } from '../services/managerService';
import './ManagerDashboard.css';

const DEPT_COLORS = {
  'Kỹ thuật':  '#1f6f3f',
  'Kinh doanh': '#3b82f6',
  'Vận hành':  '#dc2626',
  default:      '#94a3b8',
};

const PAGE_SIZE = 8;

function pad(n) {
  return String(n).padStart(2, '0');
}

export default function ManagerDashboard() {
  const [analytics, setAnalytics]     = useState(null);
  const [stats, setStats]             = useState(null);
  const [search, setSearch]           = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [page, setPage]               = useState(0);
  const [loading, setLoading]         = useState(true);
  const [errorMsg, setErrorMsg]       = useState('');
  const [selectedDate, setSelectedDate] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  });

  // Debounce search
  useEffect(() => {
    const h = setTimeout(() => setSearch(searchInput), 350);
    return () => clearTimeout(h);
  }, [searchInput]);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setErrorMsg('');

    Promise.allSettled([getDailyAnalytics(selectedDate, search), getStats()])
      .then(([analyticsRes, statsRes]) => {
        if (!isMounted) return;
        if (analyticsRes.status === 'fulfilled') setAnalytics(analyticsRes.value.data?.data);
        if (statsRes.status      === 'fulfilled') setStats(statsRes.value.data?.data);
        if (analyticsRes.status === 'rejected' && statsRes.status === 'rejected') {
          setErrorMsg('Không thể tải dữ liệu. Vui lòng thử lại sau.');
        }
      })
      .finally(() => { if (isMounted) setLoading(false); });

    return () => { isMounted = false; };
  }, [search, selectedDate]);

  useEffect(() => { setPage(0); }, [search, selectedDate]);

  const records = useMemo(() => {
    const raw = analytics?.records || [];
    return Array.isArray(raw) ? raw : [];
  }, [analytics]);

  const totalRecords = records.length;
  const pageCount    = Math.max(1, Math.ceil(totalRecords / PAGE_SIZE));
  const pagedRecords = records.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

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

  const onTimeRate    = stats?.rate;
  const checkedIn     = analytics?.present  ?? stats?.today;
  const lateCount     = analytics?.late     ?? stats?.late;
  const notCheckedIn  = analytics?.absent   ?? stats?.absent;
  const totalStaff    = analytics?.total_employees ?? stats?.total;

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar statusLabel="Đang hoạt động" />
        <main className="md">
          <div className="md__header">
            <div>
              <h1 className="md__title">Thống kê chấm công</h1>
              <p className="md__subtitle">
                {typeof checkedIn === 'number'
                  ? `Ngày ${selectedDate}: ${checkedIn} nhân sự đã điểm danh.`
                  : 'Theo dõi tình hình điểm danh nhân viên.'}
              </p>
            </div>
            <div className="md__header-actions">
              <div className="md__date-pick">
                <Calendar size={15} strokeWidth={2} />
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
              </div>
              <button className="md__export" onClick={() => window.print()}>
                <Download size={16} strokeWidth={2.2} />
                Xuất báo cáo
              </button>
            </div>
          </div>

          {errorMsg && <div className="md__alert">{errorMsg}</div>}

          {/* Metric cards */}
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
              <div className="md__metric-trend md__metric-trend--up">↗ Đúng giờ: {analytics?.on_time ?? '--'}</div>
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
                <div className="md__metric-label">VẮNG MẶT</div>
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

          {/* Main grid */}
          <div className="md__main-grid">
            {/* Donut chart */}
            <div className="md__panel">
              <h2 className="md__panel-title">Theo phòng ban</h2>
              {deptBreakdown.length === 0 ? (
                <div className="md__empty">Chưa có dữ liệu phân bổ.</div>
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
                          <Cell key={entry.name} fill={DEPT_COLORS[entry.name] || DEPT_COLORS.default} />
                        ))}
                      </Pie>
                    </PieChart>
                    <div className="md__donut-center">
                      <div className="md__donut-total">{totalCount}</div>
                      <div className="md__donut-label">Có mặt</div>
                    </div>
                  </div>
                  <ul className="md__legend">
                    {deptBreakdown.map((d) => (
                      <li key={d.name} className="md__legend-item">
                        <span className="md__legend-dot" style={{ background: DEPT_COLORS[d.name] || DEPT_COLORS.default }} />
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

            {/* Attendance table */}
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
                      <th>Vào ca</th>
                      <th>Ra ca</th>
                      <th>Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      Array.from({ length: PAGE_SIZE }).map((_, i) => (
                        <tr key={i}>
                          <td colSpan={5}><div className="md__skeleton-row" /></td>
                        </tr>
                      ))
                    ) : pagedRecords.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="md__empty-cell">Không tìm thấy nhân viên phù hợp.</td>
                      </tr>
                    ) : (
                      pagedRecords.map((rec, idx) => {
                        const checkinTime = rec.checkin_time
                          ? new Date(rec.checkin_time.replace(' ', 'T')).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
                          : '--:--';
                        const checkoutTime = rec.checkout_time
                          ? new Date(rec.checkout_time.replace(' ', 'T')).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
                          : '--:--';
                        const statusRaw = (rec.status || '').toLowerCase();
                        let statusLabel = rec.status || 'Vắng mặt';
                        let statusClass = 'md__badge--muted';
                        if (statusRaw.includes('muộn'))  { statusLabel = 'Đi muộn';  statusClass = 'md__badge--danger';  }
                        else if (statusRaw.includes('đúng')) { statusLabel = 'Đúng giờ'; statusClass = 'md__badge--success'; }
                        else if (statusRaw.includes('vắng') || !rec.status) { statusLabel = 'Vắng mặt'; statusClass = 'md__badge--muted'; }

                        return (
                          <tr key={rec.user_id || idx}>
                            <td>
                              <div className="md__person">
                                <span className="md__avatar" />
                                {rec.name || '—'}
                              </div>
                            </td>
                            <td className="md__muted-text">{rec.department || '—'}</td>
                            <td className="md__muted-text">{checkinTime}</td>
                            <td className="md__muted-text">{checkoutTime}</td>
                            <td><span className={`md__badge ${statusClass}`}>{statusLabel}</span></td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              <div className="md__table-footer">
                <span>Hiển thị {pagedRecords.length} trong {totalRecords} bản ghi</span>
                <div className="md__pagination">
                  <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))} aria-label="Trang trước">
                    <ChevronLeft size={16} />
                  </button>
                  <button disabled={page >= pageCount - 1} onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))} aria-label="Trang sau">
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}