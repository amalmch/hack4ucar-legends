import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import Login from './pages/auth/Login';
import Signup from './pages/auth/Signup';
import AdminDashboard from './pages/admin/AdminDashboard';
import TeacherPortal from './pages/teacher/TeacherPortal';
import StudentPortal from './pages/student/StudentPortal';
import UCARDashboard from './pages/ucar/UCARDashboard';
import InstitutionDashboard from './pages/institution/InstitutionDashboard';
import UCARBot from './components/UCARBot';
import NotificationsPage from './pages/notifications/NotificationsPage';
import ProfilePage from './pages/profile/ProfilePage';
import './index.css';

// Protected Route — checks auth + optional role whitelist
function ProtectedRoute({ children, allowedRoles }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={defaultRouteFor(user.role)} replace />;
  }
  return children;
}

function defaultRouteFor(role) {
  if (role === 'superucaradmin')  return '/ucar';
  if (role === 'institution_admin') return '/institution';
  if (role === 'teacher')           return '/teacher';
  return '/student';
}

// Authenticated page layout with sidebar
function Layout({ children }) {
  const { user } = useAuth();
  return (
    <div className="app-container">
      <Sidebar role={user?.role} />
      <main className="main-content">
        {children}
      </main>
      <UCARBot />
    </div>
  );
}

// Smart root redirect based on role
function RootRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={defaultRouteFor(user.role)} replace />;
}

function AppRoutes() {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login"  element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* UCAR Super Admin */}
        <Route path="/ucar" element={
          <ProtectedRoute allowedRoles={['superucaradmin']}>
            <Layout><UCARDashboard /></Layout>
          </ProtectedRoute>
        } />

        {/* Institution Admin + Super Admin */}
        <Route path="/institution" element={
          <ProtectedRoute allowedRoles={['institution_admin', 'superucaradmin']}>
            <Layout><InstitutionDashboard /></Layout>
          </ProtectedRoute>
        } />

        {/* Teacher */}
        <Route path="/teacher" element={
          <ProtectedRoute allowedRoles={['teacher']}>
            <Layout><TeacherPortal /></Layout>
          </ProtectedRoute>
        } />

        {/* Student */}
        <Route path="/student" element={
          <ProtectedRoute allowedRoles={['student']}>
            <Layout><StudentPortal /></Layout>
          </ProtectedRoute>
        } />

        {/* Fallback admin (old route) */}
        <Route path="/admin" element={
          <ProtectedRoute allowedRoles={['superucaradmin', 'institution_admin']}>
            <Layout><AdminDashboard /></Layout>
          </ProtectedRoute>
        } />

        {/* Notifications — all roles */}
        <Route path="/notifications" element={
          <ProtectedRoute allowedRoles={['superucaradmin', 'institution_admin', 'teacher', 'student']}>
            <Layout><NotificationsPage /></Layout>
          </ProtectedRoute>
        } />

        {/* Profile — all roles */}
        <Route path="/profile" element={
          <ProtectedRoute allowedRoles={['superucaradmin', 'institution_admin', 'teacher', 'student']}>
            <Layout><ProfilePage /></Layout>
          </ProtectedRoute>
        } />

        {/* Root redirect */}
        <Route path="/" element={<RootRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
