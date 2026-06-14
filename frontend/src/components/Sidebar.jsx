import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
  ScanFace,
  Fingerprint,
  BarChart3,
  UserPlus,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Sidebar.css';

const employeeLinks = [
  { to: '/trang-chu', label: 'Trang chủ', icon: LayoutGrid },
  { to: '/dang-ky-khuon-mat', label: 'Đăng ký khuôn mặt', icon: ScanFace },
  { to: '/diem-danh', label: 'Điểm danh', icon: Fingerprint },
  { to: '/thong-ke', label: 'Thống kê', icon: BarChart3 },
];

const managerExtra = { to: '/cap-tai-khoan', label: 'Cấp tài khoản', icon: UserPlus };

export default function Sidebar({ statusLabel }) {
  const { user, isManager } = useAuth();
  const links = isManager ? [...employeeLinks, managerExtra] : employeeLinks;

  const greetingName = isManager ? 'Quản lý' : (user?.name || 'User');
  const initial = greetingName.trim().charAt(0).toUpperCase();

  return (
    <aside className="sidebar">
      <div className="sidebar__profile">
        <div className={`sidebar__avatar ${isManager ? 'sidebar__avatar--manager' : ''}`}>
          {initial}
        </div>
        <div>
          <div className="sidebar__greeting">Xin chào, {greetingName}</div>
          <div className="sidebar__subtitle">Hệ thống điểm danh</div>
        </div>
      </div>

      <nav className="sidebar__nav">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
            }
          >
            <Icon size={19} strokeWidth={1.9} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {statusLabel && (
        <div className="sidebar__status">
          <div className="sidebar__status-label">TRẠNG THÁI HỆ THỐNG</div>
          <div className="sidebar__status-value">
            <span className="sidebar__status-dot" />
            {statusLabel}
          </div>
        </div>
      )}
    </aside>
  );
}
