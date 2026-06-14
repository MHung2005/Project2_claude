import api from './api';

export const loginEmployee = (username, password) =>
  api.post('/auth/employee/login', { username, password });

export const loginManager = (username, password) =>
  api.post('/auth/login', { username, password });

export const getMe = () => api.get('/auth/me');
