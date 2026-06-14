import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children, role }) {
  const { isAuthenticated, role: userRole } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (role && userRole !== role) {
    // Redirect to the correct home for each role
    return <Navigate to={userRole === 'manager' ? '/quan-ly' : '/doi-mat-khau'} replace />;
  }

  return children;
}