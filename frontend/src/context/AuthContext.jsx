import { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('fg_token'));
  const [role, setRole] = useState(() => localStorage.getItem('fg_role'));
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('fg_user');
    return stored ? JSON.parse(stored) : null;
  });

  const login = useCallback((newToken, newRole, newUser) => {
    localStorage.setItem('fg_token', newToken);
    localStorage.setItem('fg_role', newRole);
    if (newUser) localStorage.setItem('fg_user', JSON.stringify(newUser));
    setToken(newToken);
    setRole(newRole);
    setUser(newUser || null);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('fg_token');
    localStorage.removeItem('fg_role');
    localStorage.removeItem('fg_user');
    setToken(null);
    setRole(null);
    setUser(null);
  }, []);

  const value = {
    token,
    role,
    user,
    isAuthenticated: !!token,
    isManager: role === 'manager',
    isEmployee: role === 'employee',
    login,
    logout,
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
