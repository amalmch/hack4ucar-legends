import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5001',
});

// Interceptor to attach the token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ucar_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
