import { useCallback, useRef, useState } from 'react';
import { UploadCloud, FileSpreadsheet, Download, UserPlus, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { bulkImportEmployees } from '../services/managerService';
import { useToast } from '../components/Toast';
import './BulkImport.css';

export default function BulkImport() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);
  const { showToast } = useToast();

  const handleFiles = useCallback((files) => {
    const f = files?.[0];
    if (!f) return;
    const allowed = ['.xlsx', '.csv', '.xls'];
    const isAllowed = allowed.some((ext) => f.name.toLowerCase().endsWith(ext));
    if (!isAllowed) {
      showToast('Chỉ hỗ trợ định dạng XLSX hoặc CSV.', 'error');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      showToast('Kích thước file vượt quá 10MB.', 'error');
      return;
    }
    setFile(f);
    setResult(null);
  }, [showToast]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleSubmit = async () => {
    if (!file) {
      showToast('Vui lòng chọn file Excel/CSV trước.', 'error');
      return;
    }
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
  const foundCount = previewRows.length;

  return (
    <div className="page">
      <TopNav showRoleSwitch />
      <div className="page__body">
        <Sidebar statusLabel="Đang hoạt động" />
        <main className="bi">
          <h1 className="bi__title">Cấp tài khoản nhân viên</h1>
          <p className="bi__subtitle">Nhập danh sách tài khoản người dùng bằng tệp Excel.</p>

          <div className="bi__grid">
            <div className="bi__left">
              <div className="bi__card">
                <div className="bi__card-header">
                  <h2>Tải lên danh sách</h2>
                  <a
                    className="bi__sample-link"
                    href="data:text/csv;charset=utf-8,user_id,name,department,position%0A"
                    download="mau_nhan_vien.csv"
                  >
                    <Download size={14} strokeWidth={2.2} />
                    Tải file Excel mẫu
                  </a>
                </div>

                <div
                  className={`bi__dropzone ${dragging ? 'bi__dropzone--active' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                  }}
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

              <div className="bi__notes">
                <ul>
                  <li>Đảm bảo dữ liệu đúng định dạng cột trong file mẫu.</li>
                  <li>Mã nhân viên (user_id) phải là duy nhất và chưa tồn tại trên hệ thống.</li>
                  <li>Mật khẩu mặc định sẽ được gửi qua email nhân viên.</li>
                </ul>
              </div>
            </div>

            <div className="bi__right">
              <div className="bi__card bi__preview">
                <div className="bi__card-header">
                  <h2>Xem trước dữ liệu</h2>
                  {result && !result.error && (
                    <span className="bi__found-badge">{foundCount} nhân viên tìm thấy</span>
                  )}
                </div>

                {result?.error ? (
                  <div className="bi__import-error">
                    <XCircle size={18} strokeWidth={2.2} />
                    {result.error}
                  </div>
                ) : !result ? (
                  <div className="bi__placeholder">
                    Tải lên một file để xem trước dữ liệu trước khi tạo tài khoản.
                  </div>
                ) : previewRows.length === 0 ? (
                  <div className="bi__placeholder">Không có dữ liệu xem trước từ máy chủ.</div>
                ) : (
                  <div className="bi__table-scroll">
                    <table className="bi__table">
                      <thead>
                        <tr>
                          <th>STT</th>
                          <th>Họ tên</th>
                          <th>Email</th>
                          <th>Phòng ban</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewRows.map((row, idx) => (
                          <tr key={idx}>
                            <td>{String(idx + 1).padStart(2, '0')}</td>
                            <td className="bi__name-cell">{row.name || row.full_name || '—'}</td>
                            <td className="bi__muted-text">{row.email || '—'}</td>
                            <td className="bi__muted-text">{row.department || '—'}</td>
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
                      <div className="bi__summary-item">
                        Đã bỏ qua: {result.skipped_count}
                      </div>
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
                    <>
                      <Loader2 size={18} className="bi__spin" /> Đang xử lý...
                    </>
                  ) : (
                    <>
                      <UserPlus size={18} strokeWidth={2.2} />
                      Xác nhận tạo tài khoản hàng loạt
                    </>
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