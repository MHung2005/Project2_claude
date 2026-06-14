import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './components/Toast';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import ChangePassword from './pages/ChangePassword';
import FaceRegister from './pages/FaceRegister';
import CheckIn from './pages/CheckIn';
import StatsPage from './pages/StatsPage';
import ManagerDashboard from './pages/ManagerDashboard';
import BulkImport from './pages/BulkImport';
import EmployeeDashboard from './pages/EmployeeDashboard';
import './styles/global.css';

function RootRedirect() {
  const { isAuthenticated, isManager } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={isManager ? '/quan-ly' : '/trang-chu'} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/login" element={<Login />} />

            {/* ── EMPLOYEE routes ── */}
            <Route
              path="/trang-chu"
              element={
                <ProtectedRoute role="employee">
                  <EmployeeDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/doi-mat-khau"
              element={
                <ProtectedRoute role="employee">
                  <ChangePassword />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dang-ky-khuon-mat"
              element={
                <ProtectedRoute role="employee">
                  <FaceRegister />
                </ProtectedRoute>
              }
            />
            <Route
              path="/diem-danh"
              element={
                <ProtectedRoute role="employee">
                  <CheckIn />
                </ProtectedRoute>
              }
            />
            <Route
              path="/thong-ke"
              element={
                <ProtectedRoute role="employee">
                  <StatsPage />
                </ProtectedRoute>
              }
            />

            {/* ── MANAGER routes ── */}
            <Route
              path="/quan-ly"
              element={
                <ProtectedRoute role="manager">
                  <ManagerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/cap-tai-khoan"
              element={
                <ProtectedRoute role="manager">
                  <BulkImport />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}