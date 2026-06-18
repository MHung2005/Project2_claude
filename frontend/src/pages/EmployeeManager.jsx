import { useCallback, useEffect, useState } from 'react';
import {
  Search, Pencil, Trash2, X, Loader2, CheckCircle2,
  ChevronLeft, ChevronRight, Users, ScanFace, AlertTriangle,
  User, Building2, Briefcase,
} from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import {
  listEmployees,
  updateEmployee,
  deleteEmployee,
} from '../services/managerService';
import { useToast } from '../components/Toast';
import './EmployeeManager.css';

const PAGE_SIZE = 10;


// ── Modal: Sửa thông tin nhân viên ────────────────────────────────────────
function EditModal({ employee, onClose, onSuccess }) {
  const { showToast } = useToast();
  const [form, setForm]     = useState({
    name:       employee.name       || '',
    department: employee.department || '',
    position:   employee.position   || '',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors]   = useState({});

  const handleField = (key) => (e) => {
    setForm((p) => ({ ...p, [key]: e.target.value }));
    setErrors((p) => ({ ...p, [key]: '' }));
  };

  const validate = () => {
    const e = {};
    if (!form.name.trim())       e.name       = 'Bắt buộc';
    if (!form.department.trim()) e.department = 'Bắt buộc';
    if (!form.position.trim())   e.position   = 'Bắt buộc';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await updateEmployee(employee.user_id, form);
      showToast(`Đã cập nhật thông tin ${form.name}.`, 'success');
      onSuccess();
    } catch (err) {
      const msg = err?.response?.data?.message || 'Cập nhật thất bại.';
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="em-modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="em-modal em-modal--sm">
        <div className="em-modal__header">
          <div>
            <h2 className="em-modal__title">Chỉnh sửa nhân viên</h2>
            <p className="em-modal__subtitle">Mã NV: <strong>{employee.user_id}</strong></p>
          </div>
          <button className="em-modal__close" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="em-modal__body">
          <div className="em-form-grid">
            <ModalField
              icon={<User size={15} />}
              label="Họ và tên"
              placeholder="Nhập họ và tên"
              value={form.name}
              onChange={handleField('name')}
              error={errors.name}
            />
            <ModalField
              icon={<Building2 size={15} />}
              label="Phòng ban"
              placeholder="Nhập phòng ban"
              value={form.department}
              onChange={handleField('department')}
              error={errors.department}
            />
            <ModalField
              icon={<Briefcase size={15} />}
              label="Chức vụ"
              placeholder="Nhập chức vụ"
              value={form.position}
              onChange={handleField('position')}
              error={errors.position}
            />
          </div>
        </div>

        <div className="em-modal__footer">
          <button className="em-btn em-btn--ghost" onClick={onClose} disabled={loading}>Huỷ</button>
          <button className="em-btn em-btn--primary" onClick={handleSubmit} disabled={loading}>
            {loading ? <><Loader2 size={16} className="em-spin" /> Đang lưu...</> : <><CheckCircle2 size={16} /> Lưu thay đổi</>}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Xác nhận xoá ───────────────────────────────────────────────────
function DeleteModal({ employee, onClose, onSuccess }) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    setLoading(true);
    try {
      await deleteEmployee(employee.user_id);
      showToast(`Đã xoá nhân viên ${employee.name}.`, 'success');
      onSuccess();
    } catch (err) {
      const msg = err?.response?.data?.message || 'Xoá thất bại.';
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="em-modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="em-modal em-modal--xs">
        <div className="em-modal__header">
          <div className="em-delete-icon"><AlertTriangle size={22} strokeWidth={2} /></div>
          <button className="em-modal__close" onClick={onClose}><X size={20} /></button>
        </div>
        <div className="em-modal__body em-modal__body--center">
          <h2 className="em-modal__title">Xoá nhân viên?</h2>
          <p className="em-delete-desc">
            Hành động này sẽ xoá vĩnh viễn hồ sơ, tài khoản và dữ liệu khuôn mặt của&nbsp;
            <strong>{employee.name}</strong> (mã: {employee.user_id}).<br />Không thể hoàn tác.
          </p>
        </div>
        <div className="em-modal__footer">
          <button className="em-btn em-btn--ghost" onClick={onClose} disabled={loading}>Giữ lại</button>
          <button className="em-btn em-btn--danger" onClick={handleDelete} disabled={loading}>
            {loading ? <><Loader2 size={16} className="em-spin" /> Đang xoá...</> : <><Trash2 size={16} /> Xoá nhân viên</>}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Shared: ô nhập liệu trong modal ──────────────────────────────────────
function ModalField({ icon, label, placeholder, value, onChange, error }) {
  return (
    <div className="em-field">
      <label className="em-field__label">{label}</label>
      <div className="em-field__wrap">
        <span className="em-field__icon">{icon}</span>
        <input
          className={`em-field__input ${error ? 'em-field__input--error' : ''}`}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
        />
      </div>
      {error && <p className="em-field-error">{error}</p>}
    </div>
  );
}

// ── Avatar initials ───────────────────────────────────────────────────────
function Avatar({ name, status }) {
  const initials = (name || 'NV')
    .trim().split(' ').map((p) => p[0]).filter(Boolean).slice(-2).join('').toUpperCase();
  return (
    <div className={`em-row-avatar ${status === 'approved' ? 'em-row-avatar--ok' : ''}`}>
      {initials}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────
export default function EmployeeManager() {
  const { showToast } = useToast();

  const [employees, setEmployees]     = useState([]);
  const [total, setTotal]             = useState(0);
  const [loading, setLoading]         = useState(true);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch]           = useState('');
  const [page, setPage]               = useState(0);
  const [errorMsg, setErrorMsg]       = useState('');

  // Modal states
  const [editTarget, setEditTarget]   = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Debounce search
  useEffect(() => {
    const h = setTimeout(() => { setSearch(searchInput); setPage(0); }, 350);
    return () => clearTimeout(h);
  }, [searchInput]);

  const load = useCallback(() => {
    setLoading(true);
    setErrorMsg('');
    listEmployees(search)
      .then(({ data: payload }) => {
        // Backend: { success, message, data: { total, employees: [...] } }
        const data = payload?.data;
        setEmployees(Array.isArray(data?.employees) ? data.employees : []);
        setTotal(data?.total ?? 0);
      })
      .catch(() => setErrorMsg('Không thể tải danh sách nhân viên. Vui lòng thử lại.'))
      .finally(() => setLoading(false));
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const pageCount    = Math.max(1, Math.ceil(employees.length / PAGE_SIZE));
  const pagedRows    = employees.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const approvedCount = employees.filter((e) => e.biometric_status === 'approved').length;
  const pendingCount  = employees.length - approvedCount;

  const handleSuccess = () => {
    setEditTarget(null);
    setDeleteTarget(null);
    load();
  };

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar statusLabel="Đang hoạt động" />

        <main className="em">
          {/* Header */}
          <div className="em__header">
            <div>
              <h1 className="em__title">Quản lý nhân viên</h1>
              <p className="em__subtitle">Xem, sửa, xoá và theo dõi trạng thái nhân viên.</p>
            </div>
          </div>

          {/* Stat chips */}
          <div className="em__chips">
            <div className="em__chip">
              <Users size={15} strokeWidth={2} />
              <span><strong>{total}</strong> nhân viên</span>
            </div>
            <div className="em__chip em__chip--ok">
              <ScanFace size={15} strokeWidth={2} />
              <span><strong>{approvedCount}</strong> đã đăng ký khuôn mặt</span>
            </div>
            {pendingCount > 0 && (
              <div className="em__chip em__chip--warn">
                <AlertTriangle size={15} strokeWidth={2} />
                <span><strong>{pendingCount}</strong> chưa đăng ký</span>
              </div>
            )}
          </div>

          {errorMsg && <div className="em__alert">{errorMsg}</div>}

          {/* Table card */}
          <div className="em__card">
            {/* Toolbar */}
            <div className="em__toolbar">
              <div className="em__search">
                <Search size={16} strokeWidth={2} />
                <input
                  type="text"
                  placeholder="Tìm tên, phòng ban, chức vụ..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                />
                {searchInput && (
                  <button className="em__search-clear" onClick={() => setSearchInput('')}>
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>

            {/* Table */}
            <div className="em__table-scroll">
              <table className="em__table">
                <thead>
                  <tr>
                    <th>Nhân viên</th>
                    <th>Mã NV</th>
                    <th>Phòng ban</th>
                    <th>Chức vụ</th>
                    <th>Khuôn mặt</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    Array.from({ length: PAGE_SIZE }).map((_, i) => (
                      <tr key={i}>
                        <td colSpan={6}><div className="em__skeleton" /></td>
                      </tr>
                    ))
                  ) : pagedRows.length === 0 ? (
                    <tr>
                      <td colSpan={6}>
                        <div className="em__empty">
                          <Users size={32} strokeWidth={1.4} />
                          <span>
                            {search ? `Không tìm thấy nhân viên nào với "${search}"` : 'Chưa có nhân viên nào trong hệ thống.'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    pagedRows.map((emp) => (
                      <tr key={emp.user_id} className="em__row">
                        <td>
                          <div className="em__person">
                            <Avatar name={emp.name} status={emp.biometric_status} />
                            <div>
                              <div className="em__person-name">{emp.name || '—'}</div>
                              <div className="em__person-id">{emp.user_id}</div>
                            </div>
                          </div>
                        </td>
                        <td className="em__muted">{emp.user_id}</td>
                        <td>{emp.department || <span className="em__muted">—</span>}</td>
                        <td>{emp.position   || <span className="em__muted">—</span>}</td>
                        <td>
                          <span className={`em__badge ${emp.biometric_status === 'approved' ? 'em__badge--ok' : 'em__badge--none'}`}>
                            {emp.biometric_status === 'approved' ? 'Đã đăng ký' : 'Chưa đăng ký'}
                          </span>
                        </td>
                        <td>
                          <div className="em__row-actions">
                            <button
                              className="em__action-btn em__action-btn--edit"
                              onClick={() => setEditTarget(emp)}
                              title="Sửa thông tin"
                            >
                              <Pencil size={15} strokeWidth={2} />
                            </button>
                            <button
                              className="em__action-btn em__action-btn--delete"
                              onClick={() => setDeleteTarget(emp)}
                              title="Xoá nhân viên"
                            >
                              <Trash2 size={15} strokeWidth={2} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="em__table-footer">
              <span className="em__muted">
                {loading ? '...' : `Hiển thị ${pagedRows.length} / ${employees.length} nhân viên`}
              </span>
              <div className="em__pagination">
                <button
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  aria-label="Trang trước"
                >
                  <ChevronLeft size={16} />
                </button>
                {Array.from({ length: pageCount }).map((_, i) => (
                  <button
                    key={i}
                    className={i === page ? 'em__pagination-active' : ''}
                    onClick={() => setPage(i)}
                  >
                    {i + 1}
                  </button>
                ))}
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
        </main>
      </div>

      {/* Modals */}
      {editTarget && <EditModal   employee={editTarget} onClose={() => setEditTarget(null)}   onSuccess={handleSuccess} />}
      {deleteTarget && <DeleteModal employee={deleteTarget} onClose={() => setDeleteTarget(null)} onSuccess={handleSuccess} />}
    </div>
  );
}