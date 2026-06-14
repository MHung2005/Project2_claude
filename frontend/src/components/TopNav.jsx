import { Bell, Settings } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './TopNav.css';

export default function TopNav({ showRoleSwitch = false, showSettings = false }) {
  const { user, role, isManager, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const initials = (user?.name || (isManager ? 'Quản lý' : 'User'))
    .split(' ')
    .map((p) => p[0])
    .slice(-2)
    .join('')
    .toUpperCase();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="topnav">
      <div className="topnav__brand">FaceTime &amp; GPS</div>

      {showRoleSwitch && (
        <nav className="topnav__tabs">
          <Link
            to="/trang-chu"
            className={`topnav__tab ${location.pathname.startsWith('/trang-chu') || ['/diem-danh', '/dang-ky-khuon-mat', '/thong-ke'].some((p) => location.pathname.startsWith(p)) ? 'topnav__tab--active' : ''}`}
          >
            Nhân viên
          </Link>
          <Link
            to="/quan-ly"
            className={`topnav__tab ${location.pathname.startsWith('/quan-ly') || location.pathname.startsWith('/cap-tai-khoan') ? 'topnav__tab--active' : ''}`}
          >
            Quản lý
          </Link>
        </nav>
      )}

      <div className="topnav__right">
        <button className="topnav__icon-btn" aria-label="Thông báo">
          <Bell size={20} strokeWidth={1.8} />
        </button>
        {showSettings && (
          <button className="topnav__icon-btn" aria-label="Cài đặt">
            <Settings size={20} strokeWidth={1.8} />
          </button>
        )}
        <button className="topnav__avatar" onClick={handleLogout} title="Đăng xuất">
          {initials}
        </button>
      </div>
    </header>
  );
}
