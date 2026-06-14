import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Lock, ScanFace, MapPin } from 'lucide-react';
import { loginEmployee, loginManager } from '../services/authService';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import './Login.css';

export default function Login() {
  const [mode, setMode] = useState('employee'); // 'employee' | 'manager'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const navigate = useNavigate();
  const { login } = useAuth();
  const { showToast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.');
      return;
    }
    setLoading(true);
    try {
      const apiCall = mode === 'manager' ? loginManager : loginEmployee;
      const { data: payload } = await apiCall(username, password);
      const data = payload?.data;

      const token = data?.access_token || data?.token;
      if (!token) {
        throw new Error('Phản hồi không hợp lệ từ máy chủ.');
      }

      const role = data?.role || mode;
      const user = data?.user || {
        name: data?.name,
        username: data?.username || username,
        user_id: data?.user_id,
      };

      login(token, role, user);
      showToast('Đăng nhập thành công', 'success');
      navigate(role === 'manager' ? '/quan-ly' : '/trang-chu');
    } catch (err) {
      const detail = err?.response?.data?.message || err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : detail || 'Tên đăng nhập hoặc mật khẩu không đúng.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login">
      <div className="login__hero">
        <div className="login__logo">
          <ScanFace size={34} strokeWidth={1.8} />
        </div>
        <h1 className="login__title">FaceTime &amp; GPS</h1>
        <p className="login__subtitle">Hệ thống điểm danh thông minh</p>
      </div>

      <div className="login__card">
        <div className="login__role-switch">
          <button
            type="button"
            className={`login__role-btn ${mode === 'employee' ? 'login__role-btn--active' : ''}`}
            onClick={() => setMode('employee')}
          >
            Nhân viên
          </button>
          <button
            type="button"
            className={`login__role-btn ${mode === 'manager' ? 'login__role-btn--active' : ''}`}
            onClick={() => setMode('manager')}
          >
            Quản lý
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <label className="login__label" htmlFor="username">
            Tên đăng nhập hoặc Email
          </label>
          <div className="login__input-wrap">
            <User size={18} strokeWidth={1.8} className="login__input-icon" />
            <input
              id="username"
              className="login__input"
              type="text"
              placeholder="nguyen.van.a@company.com"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>

          <div className="login__label-row">
            <label className="login__label" htmlFor="password">
              Mật khẩu
            </label>
            <a href="#" className="login__forgot" onClick={(e) => e.preventDefault()}>
              Quên mật khẩu?
            </a>
          </div>
          <div className="login__input-wrap">
            <Lock size={18} strokeWidth={1.8} className="login__input-icon" />
            <input
              id="password"
              className="login__input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          <label className="login__remember">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            Ghi nhớ đăng nhập
          </label>

          {error && <div className="login__error">{error}</div>}

          <button type="submit" className="login__submit" disabled={loading}>
            {loading ? 'Đang đăng nhập...' : 'Đăng Nhập'}
          </button>
        </form>

        <div className="login__divider">
          <span>HOẶC ĐĂNG NHẬP NHANH</span>
        </div>

        <div className="login__faceid">
          <button
            type="button"
            className="login__faceid-btn"
            onClick={() => showToast('Vui lòng đăng nhập trước để dùng FaceID', 'error')}
            aria-label="Đăng nhập bằng FaceID"
          >
            <ScanFace size={26} strokeWidth={1.8} />
          </button>
          <span className="login__faceid-label">FaceID Integration</span>
        </div>
      </div>

      <div className="login__footer">
        <span className="login__footer-item">
          <MapPin size={14} strokeWidth={1.8} /> GPS Verified Security
        </span>
        <span className="login__footer-version">Version 2.4.0 • Enterprise Edition</span>
      </div>
    </div>
  );
}