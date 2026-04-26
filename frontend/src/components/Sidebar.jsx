import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, BookOpen, Bell, Building2, LogOut, Shield, GraduationCap, UserCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Sidebar({ role }) {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  const [unread, setUnread] = React.useState(0);

  React.useEffect(() => {
    async function loadUnread() {
      if (!user) return;
      try {
        const res = await api.get('/api/notifications/unread-count');
        setUnread(res.data.unread || 0);
      } catch (e) { }
    }
    loadUnread();
    // Refresh unread count every minute
    const interval = setInterval(loadUnread, 60000);
    return () => clearInterval(interval);
  }, [user]);

  const navItem = (to, Icon, label, badgeCount = 0) => (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center justify-between px-5 py-3.5 mb-2 rounded-xl font-medium transition-all duration-300 relative overflow-hidden group ${isActive
          ? 'bg-ucar-600 text-white shadow-lg shadow-ucar-600/30'
          : 'text-slate-600 hover:text-slate-900 hover:translate-x-1 hover:bg-slate-100/80'
        }`
      }
    >
      <div className="flex items-center gap-4 relative z-10">
        <Icon size={20} />
        <span>{label}</span>
      </div>
      {badgeCount > 0 && (
        <span className="relative z-10 bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full shadow-sm">
          {badgeCount > 99 ? '99+' : badgeCount}
        </span>
      )}
    </NavLink>
  );

  return (
    <aside className="w-72 bg-white border-r border-slate-200 flex flex-col p-6 shadow-sm z-10">
      <div className="flex items-center gap-3 mb-10 font-display text-2xl font-extrabold bg-accent-gradient bg-clip-text text-transparent">
        <div className="w-10 h-10 rounded-xl bg-accent-gradient shadow-lg shadow-ucar-600/30 shrink-0 flex items-center justify-center text-white text-sm tracking-tighter">
          UCAR
        </div>
        UCAR
      </div>

      <nav className="flex-1">
        {(role === 'superucaradmin') && navItem('/ucar', LayoutDashboard, 'UCAR HQ')}
        {(role === 'institution_admin' || role === 'superucaradmin') && navItem('/institution', Building2, 'Mon Établissement')}
        {(role === 'teacher') && navItem('/teacher', BookOpen, 'Mes Classes')}
        {(role === 'student') && navItem('/student', GraduationCap, 'Mon Parcours')}
        {navItem('/notifications', Bell, 'Notifications', unread)}
        {navItem('/profile', UserCircle, 'Mon Profil')}
      </nav>

      <div className="pt-5 border-t border-slate-200 mt-auto">
        <div className="p-4 bg-slate-50 rounded-xl mb-3 border border-slate-100 transition-all duration-300 hover:shadow-md">
          <p className="font-semibold text-sm mb-0.5 text-slate-900 truncate">{user?.name}</p>
          <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          <span className="inline-block mt-2 px-2.5 py-0.5 bg-accent-gradient rounded-full text-[0.65rem] font-bold text-white uppercase tracking-wider shadow-sm">
            {role?.replace('_', ' ')}
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-4 py-3 text-red-600 font-medium rounded-xl hover:bg-red-50 hover:translate-x-1 transition-all duration-300"
        >
          <LogOut size={20} /> Déconnexion
        </button>
      </div>
    </aside>
  );
}
