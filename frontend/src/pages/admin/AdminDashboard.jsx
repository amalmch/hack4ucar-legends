import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function AdminDashboard() {
  const { user } = useAuth();
  
  // Smart redirect: AdminDashboard is now a legacy route, redirecting to the specific dashboards
  if (user?.role === 'superucaradmin') return <Navigate to="/ucar" replace />;
  if (user?.role === 'institution_admin') return <Navigate to="/institution" replace />;

  return (
    <div className="flex items-center justify-center min-h-[60vh] animate-fade">
      <div className="glass-card text-center max-w-md w-full">
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Redirection...</h2>
        <p className="text-slate-500 font-medium">Vous allez être redirigé vers votre tableau de bord.</p>
      </div>
    </div>
  );
}
