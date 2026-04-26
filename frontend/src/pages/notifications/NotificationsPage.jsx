import React, { useState, useEffect } from 'react';
import api from '../../api';
import { Bell, CheckCircle, AlertTriangle, Award, FileText, Info, CheckCheck } from 'lucide-react';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get('/api/notifications');
        setNotifications(res.data.notifications || []);
        setUnread(res.data.unread || 0);
      } catch(e) { console.error(e); }
      setLoading(false);
    }
    load();
  }, []);

  const markRead = async (id) => {
    await api.patch(`/api/notifications/${id}/read`);
    setNotifications(notifications.map(n => n.id === id ? {...n, read: true} : n));
    setUnread(Math.max(0, unread - 1));
  };

  const markAllRead = async () => {
    await api.patch('/api/notifications/read-all');
    setNotifications(notifications.map(n => ({...n, read: true})));
    setUnread(0);
  };

  const iconFor = (type) => {
    if (type === 'grade') return <Award size={20}/>;
    if (type === 'warning') return <AlertTriangle size={20}/>;
    if (type === 'request_status' || type === 'request') return <FileText size={20}/>;
    if (type === 'exam_scheduled') return <Info size={20}/>;
    return <Bell size={20}/>;
  };

  const colorFor = (type) => {
    if (type === 'grade') return 'bg-blue-100 text-blue-600';
    if (type === 'warning') return 'bg-red-100 text-red-600';
    if (type === 'request_status') return 'bg-emerald-100 text-emerald-600';
    if (type === 'request') return 'bg-amber-100 text-amber-600';
    if (type === 'exam_scheduled') return 'bg-indigo-100 text-indigo-600';
    return 'bg-slate-100 text-slate-600';
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-slate-600 rounded-full animate-spin" />
        <p className="font-medium">Chargement des notifications...</p>
      </div>
    </div>
  );

  return (
    <div className="animate-fade max-w-4xl mx-auto pb-10">
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-display font-extrabold text-slate-900 tracking-tight">Notifications</h1>
          <p className="text-slate-500 font-medium text-sm mt-1">{unread > 0 ? `${unread} non lue(s)` : 'Tout est à jour'}</p>
        </div>
        {unread > 0 && (
          <button onClick={markAllRead} className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all">
            <CheckCheck size={16}/> Tout marquer comme lu
          </button>
        )}
      </header>

      {notifications.length === 0 ? (
        <div className="glass-card text-center py-16">
          <Bell size={48} className="mx-auto text-slate-300 mb-4"/>
          <h2 className="text-xl font-bold text-slate-800 mb-2">Aucune notification</h2>
          <p className="text-slate-500 font-medium">Vous serez notifié des mises à jour importantes ici.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((n,i) => (
            <div key={i}
              className={`glass-card flex items-start gap-4 transition-all cursor-pointer hover:shadow-md ${!n.read ? 'border-l-4 border-ucar-500 bg-ucar-50/20' : 'opacity-80'}`}
              onClick={() => !n.read && markRead(n.id)}>
              <div className={`p-2.5 rounded-xl ${colorFor(n.type)}`}>
                {iconFor(n.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`font-bold text-slate-800 ${n.read ? 'opacity-70' : ''}`}>{n.title}</p>
                <p className="text-sm text-slate-500 mt-1">{n.message}</p>
                <p className="text-xs text-slate-400 mt-2">{n.created_at ? new Date(n.created_at).toLocaleDateString('fr-FR', {hour:'2-digit', minute:'2-digit'}) : ''}</p>
              </div>
              {!n.read && <span className="w-3 h-3 rounded-full bg-ucar-500 shrink-0 mt-2 animate-pulse"/>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
