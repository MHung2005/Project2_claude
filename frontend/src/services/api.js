import axios from 'axios';

// Base URL for the FaceTime & GPS Attendance API
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Attach bearer token to every authenticated request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fg_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401s globally by clearing session
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('fg_token');
      localStorage.removeItem('fg_role');
      localStorage.removeItem('fg_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
