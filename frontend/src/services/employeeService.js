import api from './api';

export const getProfile = () => api.get('/employee/profile');

export const getMonthlyStats = (year, month) =>
  api.get('/employee/stats/monthly', { params: { year, month } });

export const getAttendance = (start_date, end_date) =>
  api.get('/employee/attendance', { params: { start_date, end_date } });

export const registerFace = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/employee/register-face', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const checkin = (file, lat, lng) => {
  const formData = new FormData();
  formData.append('file', file);
  if (lat !== null && lat !== undefined) formData.append('lat', lat);
  if (lng !== null && lng !== undefined) formData.append('lng', lng);
  return api.post('/employee/checkin', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const checkout = (file, lat, lng) => {
  const formData = new FormData();
  formData.append('file', file);
  if (lat !== null && lat !== undefined) formData.append('lat', lat);
  if (lng !== null && lng !== undefined) formData.append('lng', lng);
  return api.post('/employee/checkout', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
