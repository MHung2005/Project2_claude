import { useState } from 'react';
import { Lock, Eye, EyeOff, CheckCircle2, Loader2 } from 'lucide-react';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import { changePassword } from '../services/employeeService';
import { useToast } from '../components/Toast';
import './ChangePassword.css';

export default function ChangePassword() {
  const { showToast } = useToast();
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm_password: '' });
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setError('');
    setSuccess(false);
  };

  const handleSubmit = async () => {
    const { old_password, new_password, confirm_password } = form;
    if (!old_password || !new_password || !confirm_password) {
      setError('Vui lòng điền đầy đủ các trường.');
      return;
    }
    if (new_password.length < 6) {
      setError('Mật khẩu mới phải có ít nhất 6 ký tự.');
      return;
    }
    if (new_password !== confirm_password) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await changePassword(old_password, new_password);
      setSuccess(true);
      setForm({ old_password: '', new_password: '', confirm_password: '' });
      showToast('Đổi mật khẩu thành công!', 'success');
    } catch (err) {
      const detail = err?.response?.data?.message || err?.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : detail || 'Đổi mật khẩu thất bại. Vui lòng kiểm tra lại mật khẩu hiện tại.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <TopNav />
      <div className="page__body">
        <Sidebar />
        <main className="cp">
          <div className="cp__center">
            <div className="cp__icon-wrap">
              <Lock size={28} strokeWidth={1.8} />
            </div>
            <h1 className="cp__title">Thay đổi mật khẩu</h1>
            <p className="cp__subtitle">
              Đặt mật khẩu mới an toàn cho tài khoản của bạn.
            </p>

            <div className="cp__card">
              {/* Old password */}
              <div className="cp__field">
                <label className="cp__label">Mật khẩu hiện tại</label>
                <div className="cp__input-wrap">
                  <Lock size={16} className="cp__input-icon" strokeWidth={1.8} />
                  <input
                    className="cp__input"
                    type={showOld ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={form.old_password}
                    onChange={handleChange('old_password')}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="cp__eye-btn"
                    onClick={() => setShowOld((v) => !v)}
                    aria-label="Hiện/ẩn mật khẩu"
                  >
                    {showOld ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* New password */}
              <div className="cp__field">
                <label className="cp__label">Mật khẩu mới</label>
                <div className="cp__input-wrap">
                  <Lock size={16} className="cp__input-icon" strokeWidth={1.8} />
                  <input
                    className="cp__input"
                    type={showNew ? 'text' : 'password'}
                    placeholder="Tối thiểu 6 ký tự"
                    value={form.new_password}
                    onChange={handleChange('new_password')}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="cp__eye-btn"
                    onClick={() => setShowNew((v) => !v)}
                    aria-label="Hiện/ẩn mật khẩu"
                  >
                    {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {form.new_password && (
                  <PasswordStrength password={form.new_password} />
                )}
              </div>

              {/* Confirm password */}
              <div className="cp__field">
                <label className="cp__label">Xác nhận mật khẩu mới</label>
                <div className="cp__input-wrap">
                  <Lock size={16} className="cp__input-icon" strokeWidth={1.8} />
                  <input
                    className="cp__input"
                    type={showConfirm ? 'text' : 'password'}
                    placeholder="Nhập lại mật khẩu mới"
                    value={form.confirm_password}
                    onChange={handleChange('confirm_password')}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="cp__eye-btn"
                    onClick={() => setShowConfirm((v) => !v)}
                    aria-label="Hiện/ẩn mật khẩu"
                  >
                    {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {form.confirm_password && form.new_password !== form.confirm_password && (
                  <p className="cp__mismatch">Mật khẩu không khớp</p>
                )}
              </div>

              {error && <div className="cp__error">{error}</div>}

              {success && (
                <div className="cp__success">
                  <CheckCircle2 size={17} strokeWidth={2.2} />
                  Mật khẩu đã được cập nhật thành công!
                </div>
              )}

              <button
                className="cp__submit"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? (
                  <><Loader2 size={18} className="cp__spin" /> Đang xử lý...</>
                ) : (
                  <><Lock size={18} strokeWidth={2} /> Cập nhật mật khẩu</>
                )}
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function strengthInfo(pw) {
  if (pw.length < 6) return { level: 0, label: 'Quá ngắn', color: '#dc2626' };
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { level: 1, label: 'Yếu',       color: '#dc2626' };
  if (score === 2) return { level: 2, label: 'Trung bình', color: '#f59e0b' };
  if (score === 3) return { level: 3, label: 'Mạnh',      color: '#16a34a' };
  return                { level: 4, label: 'Rất mạnh',   color: '#16a34a' };
}

function PasswordStrength({ password }) {
  const { level, label, color } = strengthInfo(password);
  return (
    <div className="cp__strength">
      <div className="cp__strength-bars">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="cp__strength-bar"
            style={{ background: i <= level ? color : '#e4e8ed' }}
          />
        ))}
      </div>
      <span className="cp__strength-label" style={{ color }}>{label}</span>
    </div>
  );
}