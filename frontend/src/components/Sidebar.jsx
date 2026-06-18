import { NavLink } from 'react-router-dom';
import {
  Home,
  User,
  Lock,
  ScanFace,
  Fingerprint,
  BarChart3,
  BarChart2,
  UserPlus,
  MapPin,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Sidebar.css';

// Employee: 6 chức năng
const employeeLinks = [
  { to: '/trang-chu',          label: 'Trang chủ',           icon: Home        },
  { to: '/ho-so-ca-nhan',      label: 'Hồ sơ cá nhân',        icon: User        },
  { to: '/doi-mat-khau',       label: 'Thay đổi mật khẩu',  icon: Lock        },
  { to: '/dang-ky-khuon-mat',  label: 'Đăng ký khuôn mặt',  icon: ScanFace    },
  { to: '/diem-danh',          label: 'Điểm danh',           icon: Fingerprint },
  { to: '/thong-ke',           label: 'Thống kê',            icon: BarChart3   },
];

// Manager: 3 chức năng
const managerLinks = [
  { to: '/cap-tai-khoan', label: 'Cấp tài khoản nhân viên', icon: UserPlus  },
  { to: '/cau-hinh-gps',  label: 'Cấu hình GPS điểm danh',  icon: MapPin   },
  { to: '/quan-ly',       label: 'Xem thống kê',            icon: BarChart2 },
];

export default function Sidebar({ statusLabel }) {
  const { user, isManager } = useAuth();
  const links = isManager ? managerLinks : employeeLinks;

  const greetingName = isManager ? 'Quản lý' : (user?.name || 'User');
  const initial      = greetingName.trim().charAt(0).toUpperCase();

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
    </aside>
  );
}