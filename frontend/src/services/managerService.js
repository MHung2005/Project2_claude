import api from './api';

export const getDailyAnalytics = (date, search) =>
  api.get('/manager/analytics/daily', { params: { date, search } });

export const getStats = () => api.get('/manager/stats');

export const getWeeklyStats = () => api.get('/manager/stats/weekly');

export const getCheckinsRange = (start_date, end_date) =>
  api.get('/manager/stats/range', { params: { start_date, end_date } });

export const getAttendance = (date) =>
  api.get('/manager/attendance', { params: { date } });

export const listEmployees = (search) =>
  api.get('/manager/employees', { params: { search } });

export const createEmployee = (payload) => {
  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => formData.append(key, value));
  return api.post('/manager/employees', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const updateEmployee = (user_id, payload) =>
  api.put(`/manager/employees/${user_id}`, payload);

export const deleteEmployee = (user_id) =>
  api.delete(`/manager/employees/${user_id}`);

export const getPendingEmployees = () => api.get('/manager/employees/pending');

export const approveEmployee = (user_id, status) =>
  api.put(`/manager/employees/${user_id}/approve`, { status });

export const bulkImportEmployees = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/manager/employees/bulk-import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getLocationConfig = () => api.get('/manager/location');

export const setLocationConfig = (lat, lng, radius) =>
  api.put('/manager/location', { lat, lng, radius });

export const getSchedule = () => api.get('/manager/schedule');

export const setSchedule = (start_time, end_time) =>
  api.put('/manager/schedule', { start_time, end_time });