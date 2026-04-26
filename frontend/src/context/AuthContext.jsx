import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in on mount
    const checkAuth = async () => {
      const token = localStorage.getItem('ucar_token');
      if (token) {
        try {
          // If we had a real /me endpoint, we'd call it here to get full user details.
          // For now, we will decode the JWT or fetch user details
          const res = await api.get('/api/auth/me');
          setUser(res.data);
        } catch (error) {
          console.error("Token expired or invalid", error);
          localStorage.removeItem('ucar_token');
          setUser(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (email, password) => {
    try {
      const res = await api.post('/api/auth/login', { email, password });
      localStorage.setItem('ucar_token', res.data.token);
      setUser(res.data.user);
      return { success: true, role: res.data.user.role };
    } catch (error) {
      return { success: false, message: error.response?.data?.error || "Login failed" };
    }
  };

  const signup = async (userData) => {
    try {
      await api.post('/api/auth/register', userData);
      // Auto login after signup
      return await login(userData.email, userData.password);
    } catch (error) {
      return { success: false, message: error.response?.data?.error || "Signup failed" };
    }
  };

  const logout = () => {
    localStorage.removeItem('ucar_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
