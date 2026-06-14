import { useEffect, useState } from 'react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { getAttendance } from '../services/employeeService';
import './StatsPage.css';

function pad(n) {
  return String(n).padStart(2, '0');
}

export default function StatsPage() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [range, setRange] = useState(() => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    return {
      start: `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}`,
      end: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    };
  });

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setErrorMsg('');
    getAttendance(range.start, range.end)
      .then(({ data }) => {
        if (!isMounted) return;
        const payload = data?.data;
        const list = Array.isArray(payload) ? payload : payload?.records || [];
        setRecords(list);
      })
      .catch(() => {
        if (isMounted) setErrorMsg('Không thể tải lịch sử chấm công.');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [range]);

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar />
        <main className="sp">
          <h1 className="sp__title">Thống kê chấm công</h1>
          <p className="sp__subtitle">Lịch sử điểm danh trong khoảng thời gian đã chọn.</p>

          <div className="sp__filters">
            <div className="sp__field">
              <label>Từ ngày</label>
              <input
                type="date"
                value={range.start}
                onChange={(e) => setRange((r) => ({ ...r, start: e.target.value }))}
              />
            </div>
            <div className="sp__field">
              <label>Đến ngày</label>
              <input
                type="date"
                value={range.end}
                onChange={(e) => setRange((r) => ({ ...r, end: e.target.value }))}
              />
            </div>
          </div>

          {errorMsg && <div className="sp__alert">{errorMsg}</div>}

          <div className="sp__card">
            {loading ? (
              <div className="sp__skeleton-list">
                {[0, 1, 2, 3].map((i) => (
                  <div className="sp__skeleton-row" key={i} />
                ))}
              </div>
            ) : records.length === 0 ? (
              <div className="sp__empty">Không có dữ liệu chấm công trong khoảng thời gian này.</div>
            ) : (
              <table className="sp__table">
                <thead>
                  <tr>
                    <th>Ngày</th>
                    <th>Vào ca</th>
                    <th>Ra ca</th>
                    <th>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((rec, idx) => {
                    const checkinTime = rec.timestamp
                      ? new Date(rec.timestamp.replace(' ', 'T')).toLocaleTimeString('vi-VN', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '--:--';
                    const checkoutTime = rec.checkout_time
                      ? new Date(rec.checkout_time.replace(' ', 'T')).toLocaleTimeString('vi-VN', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '--:--';
                    return (
                      <tr key={idx}>
                        <td>{rec.date || '—'}</td>
                        <td className="sp__muted">{rec.timestamp ? checkinTime : '--:--'}</td>
                        <td className="sp__muted">{rec.checkout_time ? checkoutTime : '--:--'}</td>
                        <td>
                          <span className="sp__badge">{rec.status || 'Vắng mặt'}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}