import { useEffect, useRef, useState } from 'react';
import { Bell, Settings, LogOut, ChevronDown } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './TopNav.css';

export default function TopNav({ showRoleSwitch = false, showSettings = false }) {
  const { user, role, isManager, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const displayName = user?.name || (isManager ? 'Quản lý' : 'Nhân viên');
  const initials = displayName
    .split(' ')
    .map((p) => p[0])
    .filter(Boolean)
    .slice(-2)
    .join('')
    .toUpperCase();

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    const handleEscape = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [menuOpen]);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate('/login');
  };

  return (
    <header className="topnav">
      <div className="topnav__brand">FaceTime</div>

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
        <button className="topnav__icon-btn" aria-label="Thông báo" type="button">
          <Bell size={20} strokeWidth={1.8} />
        </button>

        {showSettings && (
          <button className="topnav__icon-btn" aria-label="Cài đặt" type="button">
            <Settings size={20} strokeWidth={1.8} />
          </button>
        )}

        <div className="topnav__user" ref={menuRef}>
          <button
            type="button"
            className="topnav__avatar-btn"
            onClick={() => setMenuOpen((v) => !v)}
            aria-haspopup="true"
            aria-expanded={menuOpen}
            title={displayName}
          >
            <span className="topnav__avatar">{initials}</span>
            <ChevronDown
              size={15}
              strokeWidth={2.2}
              className={`topnav__chevron ${menuOpen ? 'topnav__chevron--open' : ''}`}
            />
          </button>

          {menuOpen && (
            <div className="topnav__menu" role="menu">
              <div className="topnav__menu-header">
                <div className="topnav__menu-name">{displayName}</div>
                <div className="topnav__menu-role">{isManager ? 'Quản lý' : 'Nhân viên'}</div>
              </div>
              <div className="topnav__menu-divider" />
              <button
                type="button"
                className="topnav__menu-item topnav__menu-item--danger"
                onClick={handleLogout}
                role="menuitem"
              >
                <LogOut size={16} strokeWidth={2} />
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}