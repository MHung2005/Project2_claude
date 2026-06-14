import { useCallback, useRef, useState } from 'react';
import {
  UploadCloud, FileSpreadsheet, Download, UserPlus,
  CheckCircle2, XCircle, Loader2, Info,
} from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { bulkImportEmployees } from '../services/managerService';
import { useToast } from '../components/Toast';
import './BulkImport.css';

// Tạo file CSV mẫu với cột password
const SAMPLE_CSV =
  'user_id,name,department,position,username,password\n' +
  'NV001,Nguyễn Văn A,Kỹ thuật,Lập trình viên,nguyen.van.a,Pass@123\n' +
  'NV002,Trần Thị B,Kinh doanh,Nhân viên kinh doanh,tran.thi.b,Pass@456\n';

const SAMPLE_URL =
  'data:text/csv;charset=utf-8,' + encodeURIComponent(SAMPLE_CSV);

export default function BulkImport() {
  const [file, setFile]           = useState(null);
  const [dragging, setDragging]   = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult]       = useState(null);
  const inputRef                  = useRef(null);
  const { showToast }             = useToast();

  const handleFiles = useCallback((files) => {
    const f = files?.[0];
    if (!f) return;
    const allowed   = ['.xlsx', '.csv', '.xls'];
    const isAllowed = allowed.some((ext) => f.name.toLowerCase().endsWith(ext));
    if (!isAllowed) { showToast('Chỉ hỗ trợ định dạng XLSX hoặc CSV.', 'error'); return; }
    if (f.size > 10 * 1024 * 1024) { showToast('Kích thước file vượt quá 10MB.', 'error'); return; }
    setFile(f);
    setResult(null);
  }, [showToast]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleSubmit = async () => {
    if (!file) { showToast('Vui lòng chọn file Excel/CSV trước.', 'error'); return; }
    setSubmitting(true);
    setResult(null);
    try {
      const { data: payload } = await bulkImportEmployees(file);
      const data = payload?.data;
      setResult(data);
      showToast(
        `Tạo tài khoản thành công: ${data?.created_count ?? 0}, bỏ qua: ${data?.skipped_count ?? 0}.`,
        'success'
      );
    } catch (err) {
      const detail = err?.response?.data?.message || err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : detail || 'Tải file thất bại. Vui lòng kiểm tra định dạng và thử lại.';
      showToast(message, 'error');
      setResult({ error: message });
    } finally {
      setSubmitting(false);
    }
  };

  const previewRows = result?.preview || [];
  const foundCount  = previewRows.length;

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar statusLabel="Đang hoạt động" />
        <main className="bi">
          <h1 className="bi__title">Cấp tài khoản nhân viên</h1>
          <p className="bi__subtitle">
            Nhập danh sách nhân viên kèm tài khoản và mật khẩu từ file Excel/CSV.
          </p>

          <div className="bi__grid">
            {/* LEFT */}
            <div className="bi__left">
              <div className="bi__card">
                <div className="bi__card-header">
                  <h2>Tải lên danh sách</h2>
                  <a className="bi__sample-link" href={SAMPLE_URL} download="mau_nhan_vien.csv">
                    <Download size={14} strokeWidth={2.2} />
                    Tải file mẫu
                  </a>
                </div>

                <div
                  className={`bi__dropzone ${dragging ? 'bi__dropzone--active' : ''}`}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => inputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                >
                  <input
                    ref={inputRef}
                    type="file"
                    accept=".xlsx,.csv,.xls"
                    hidden
                    onChange={(e) => handleFiles(e.target.files)}
                  />
                  {file ? (
                    <>
                      <FileSpreadsheet size={36} strokeWidth={1.6} className="bi__dropzone-icon bi__dropzone-icon--file" />
                      <div className="bi__dropzone-title">{file.name}</div>
                      <div className="bi__dropzone-sub">{(file.size / 1024).toFixed(1)} KB · Nhấn để thay đổi</div>
                    </>
                  ) : (
                    <>
                      <UploadCloud size={36} strokeWidth={1.6} className="bi__dropzone-icon" />
                      <div className="bi__dropzone-title">Kéo thả file vào đây</div>
                      <div className="bi__dropzone-sub">hoặc click để chọn file từ máy tính</div>
                      <div className="bi__dropzone-meta">HỖ TRỢ: XLSX, CSV (MAX 10MB)</div>
                    </>
                  )}
                </div>
              </div>

              {/* Hướng dẫn cột */}
              <div className="bi__info-card">
                <div className="bi__info-title">
                  <Info size={15} strokeWidth={2.2} /> Cấu trúc file bắt buộc
                </div>
                <div className="bi__col-list">
                  {[
                    { col: 'user_id',    desc: 'Mã nhân viên (duy nhất)',       req: true  },
                    { col: 'name',       desc: 'Họ và tên đầy đủ',              req: true  },
                    { col: 'username',   desc: 'Tên đăng nhập',                 req: true  },
                    { col: 'password',   desc: 'Mật khẩu ban đầu',              req: true  },
                    { col: 'department', desc: 'Phòng ban',                      req: false },
                    { col: 'position',   desc: 'Chức vụ / vị trí',              req: false },
                  ].map(({ col, desc, req }) => (
                    <div key={col} className="bi__col-row">
                      <code className="bi__col-name">{col}</code>
                      <span className="bi__col-desc">{desc}</span>
                      {req && <span className="bi__col-req">Bắt buộc</span>}
                    </div>
                  ))}
                </div>
                <p className="bi__info-note">
                  Mật khẩu được mã hóa ngay khi lưu. Nhân viên có thể đổi mật khẩu sau khi đăng nhập.
                </p>
              </div>
            </div>

            {/* RIGHT */}
            <div className="bi__right">
              <div className="bi__card bi__preview">
                <div className="bi__card-header">
                  <h2>Dữ liệu đã ghi vào hệ thống</h2>
                  {result && !result.error && (
                    <span className="bi__found-badge">{foundCount} nhân viên</span>
                  )}
                </div>

                {result?.error ? (
                  <div className="bi__import-error">
                    <XCircle size={18} strokeWidth={2.2} />
                    {result.error}
                  </div>
                ) : !result ? (
                  <div className="bi__placeholder">
                    Tải lên file để xem trước dữ liệu trước khi tạo tài khoản.
                  </div>
                ) : previewRows.length === 0 ? (
                  <div className="bi__placeholder">Không có dữ liệu xem trước.</div>
                ) : (
                  <div className="bi__table-scroll">
                    <table className="bi__table">
                      <thead>
                        <tr>
                          <th>STT</th>
                          <th>Mã NV</th>
                          <th>Họ tên</th>
                          <th>Tên đăng nhập</th>
                          <th>Phòng ban</th>
                          <th>Mật khẩu</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewRows.map((row, idx) => (
                          <tr key={idx}>
                            <td>{String(idx + 1).padStart(2, '0')}</td>
                            <td className="bi__muted-text">{row.user_id || '—'}</td>
                            <td className="bi__name-cell">{row.name || row.full_name || '—'}</td>
                            <td className="bi__muted-text">{row.username || '—'}</td>
                            <td className="bi__muted-text">{row.department || '—'}</td>
                            <td className="bi__muted-text">{row.password || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {result && !result.error && (
                  <div className="bi__summary">
                    {typeof result.created_count === 'number' && (
                      <div className="bi__summary-item bi__summary-item--success">
                        <CheckCircle2 size={16} strokeWidth={2.2} /> Đã tạo: {result.created_count}
                      </div>
                    )}
                    {typeof result.skipped_count === 'number' && (
                      <div className="bi__summary-item">Đã bỏ qua: {result.skipped_count}</div>
                    )}
                    {Array.isArray(result.errors) && result.errors.length > 0 && (
                      <div className="bi__summary-item bi__summary-item--error">
                        <XCircle size={16} strokeWidth={2.2} /> Lỗi: {result.errors.length}
                      </div>
                    )}
                  </div>
                )}

                <button className="bi__submit" onClick={handleSubmit} disabled={submitting}>
                  {submitting ? (
                    <><Loader2 size={18} className="bi__spin" /> Đang xử lý...</>
                  ) : (
                    <><UserPlus size={18} strokeWidth={2.2} /> Xác nhận tạo tài khoản</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}