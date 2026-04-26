import React, { useState, useEffect } from 'react';
import api from '../../api';
import StatCard from '../../components/StatCard';
import { GraduationCap, Book, Calendar, Award, AlertTriangle, Send, Bell, CheckCircle, XCircle, Clock, FileText, Users, PlusCircle } from 'lucide-react';

const REQUEST_TYPES = ["Attestation de présence", "Attestation d'inscription", "Relevé de notes", "Certificat de scolarité", "Autre"];

export default function StudentPortal() {
  const [grades, setGrades] = useState([]);
  const [absences, setAbsences] = useState([]);
  const [requests, setRequests] = useState([]);
  const [events, setEvents] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [profile, setProfile] = useState({});
  const [overallAvg, setOverallAvg] = useState(0);
  const [eliminatedCount, setEliminatedCount] = useState(0);
  const [totalAbsences, setTotalAbsences] = useState(0);
  const [activeTab, setActiveTab] = useState('notes');
  const [loading, setLoading] = useState(true);
  const [newReq, setNewReq] = useState({type: REQUEST_TYPES[0], message: ''});
  const [newEvent, setNewEvent] = useState({title: '', club: '', date: '', description: ''});
  const [reqMsg, setReqMsg] = useState('');
  const [eventMsg, setEventMsg] = useState('');
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        const [gRes, aRes, rRes, eRes, nRes, pRes] = await Promise.all([
          api.get('/api/student/grades'),
          api.get('/api/student/absences'),
          api.get('/api/student/requests'),
          api.get('/api/student/events'),
          api.get('/api/student/notifications'),
          api.get('/api/student/profile'),
        ]);
        setGrades(gRes.data.grades || []);
        setOverallAvg(gRes.data.overall_average || 0);
        setEliminatedCount(gRes.data.eliminated_count || 0);
        setAbsences(aRes.data.absences || []);
        setTotalAbsences(aRes.data.total_absences || 0);
        setRequests(rRes.data.requests || []);
        setEvents(eRes.data.events || []);
        setNotifications(nRes.data.notifications || []);
        setUnread(nRes.data.unread || 0);
        setProfile(pRes.data || {});
      } catch(e) { console.error(e); }
      setLoading(false);
    }
    load();
  }, []);

  const handleSubmitRequest = async () => {
    try {
      const res = await api.post('/api/student/requests', newReq);
      setReqMsg(res.data.eligible ? '✅ Demande envoyée avec succès' : `⚠️ ${res.data.message}`);
      setNewReq({type: REQUEST_TYPES[0], message: ''});
      const rRes = await api.get('/api/student/requests');
      setRequests(rRes.data.requests || []);
      const nRes = await api.get('/api/student/notifications');
      setNotifications(nRes.data.notifications || []);
      setUnread(nRes.data.unread || 0);
    } catch(e) { setReqMsg('❌ Erreur lors de la soumission'); }
    setTimeout(() => setReqMsg(''), 4000);
  };

  const handleSubmitEvent = async () => {
    if (!newEvent.title || !newEvent.club || !newEvent.date) {
      setEventMsg('⚠️ Veuillez remplir tous les champs obligatoires.');
      setTimeout(() => setEventMsg(''), 4000);
      return;
    }
    try {
      await api.post('/api/student/events', newEvent);
      setEventMsg('✅ Événement soumis avec succès');
      setNewEvent({title: '', club: '', date: '', description: ''});
      const eRes = await api.get('/api/student/events');
      setEvents(eRes.data.events || []);
    } catch(e) { setEventMsg('❌ Erreur lors de la soumission'); }
    setTimeout(() => setEventMsg(''), 4000);
  };

  const markRead = async (id) => {
    await api.patch(`/api/notifications/${id}/read`);
    setNotifications(notifications.map(n => n.id === id ? {...n, read: true} : n));
    setUnread(Math.max(0, unread - 1));
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-amber-200 border-t-amber-600 rounded-full animate-spin" />
        <p className="font-medium">Chargement de votre espace...</p>
      </div>
    </div>
  );

  const tabs = ['notes','absences','demandes','events','notifications'];

  return (
    <div className="animate-fade max-w-7xl mx-auto pb-10">
      <header className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="px-3 py-1 bg-amber-50 text-amber-700 rounded-full text-xs font-bold uppercase tracking-wider border border-amber-100 shadow-sm">Espace Étudiant</span>
          {profile.niveau && <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-bold border border-blue-100">{profile.niveau} — {profile.programme}</span>}
          {profile.classe && <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold border border-emerald-100">Classe : {profile.classe}</span>}
        </div>
        <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-slate-900 mb-1 tracking-tight">
          {profile.prenom ? `Bienvenue, ${profile.prenom} ${profile.nom}` : 'Portail Étudiant'}
        </h1>
        <p className="text-slate-500 font-medium text-sm">Vos notes, absences et demandes administratives.</p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Moyenne Générale" value={overallAvg + '/20'} icon={Award} />
        <StatCard title="Matières" value={grades.length} icon={Book} />
        <StatCard title="Total Absences" value={totalAbsences} icon={Calendar} alert={totalAbsences > 10} />
        <StatCard title="Éliminé(s)" value={eliminatedCount} icon={AlertTriangle} alert={eliminatedCount > 0} />
      </div>

      <div className="flex gap-2 sm:gap-6 mb-8 border-b border-slate-200 overflow-x-auto no-scrollbar">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`whitespace-nowrap px-4 py-4 border-b-2 font-bold text-sm transition-all duration-300 ${activeTab === t ? 'border-amber-600 text-amber-700' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}>
            {t === 'notes' ? '📝 Fiche de Notes'
              : t === 'absences' ? `📅 Absences (${totalAbsences})`
              : t === 'demandes' ? '📄 Demandes'
              : t === 'events' ? '🎉 Vie Associative'
              : <span className="flex items-center gap-2">🔔 Notifications {unread > 0 && <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs">{unread}</span>}</span>
            }
          </button>
        ))}
      </div>

      {/* Notes */}
      {activeTab === 'notes' && (
        <div className="animate-fade">
          <div className="glass-card mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-slate-800">Moyenne Générale du Semestre</h3>
              <p className="text-sm text-slate-500">Calcul pondéré : DS (30%) + Examen (50%) + TP (20%)</p>
            </div>
            <div className={`text-4xl font-display font-extrabold ${overallAvg >= 10 ? 'text-emerald-600' : 'text-red-600'}`}>
              {overallAvg}/20
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead><tr><th>Matière</th><th>DS /20</th><th>Examen /20</th><th>TP /20</th><th>Moyenne</th><th>Abs.</th><th>Statut</th></tr></thead>
              <tbody>
                {grades.map((g,i) => (
                  <tr key={i} className={g.eliminated ? 'bg-red-50/50' : ''}>
                    <td className="font-bold text-slate-800">{g.subject}</td>
                    <td className={`font-semibold ${g.ds < 8 ? 'text-red-600' : 'text-slate-700'}`}>{g.eliminated ? '—' : g.ds}</td>
                    <td className={`font-semibold ${g.examen < 8 ? 'text-red-600' : 'text-slate-700'}`}>{g.eliminated ? '—' : g.examen}</td>
                    <td className="font-semibold text-slate-700">{g.eliminated ? '—' : g.tp}</td>
                    <td className={`font-bold ${g.eliminated ? 'text-red-600' : g.moyenne >= 10 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {g.eliminated ? '0' : g.moyenne}
                    </td>
                    <td className={`font-semibold ${g.absences > 3 ? 'text-red-600' : 'text-slate-600'}`}>{g.absences}</td>
                    <td>
                      {g.eliminated
                        ? <span className="px-2.5 py-1 bg-red-100 text-red-700 rounded-md text-xs font-bold border border-red-200 flex items-center gap-1 w-fit"><XCircle size={12}/> Éliminé</span>
                        : g.moyenne >= 10
                          ? <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-md text-xs font-bold border border-emerald-100 flex items-center gap-1 w-fit"><CheckCircle size={12}/> Validé</span>
                          : <span className="px-2.5 py-1 bg-amber-50 text-amber-700 rounded-md text-xs font-bold border border-amber-100 flex items-center gap-1 w-fit"><AlertTriangle size={12}/> Rattrapage</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Absences */}
      {activeTab === 'absences' && (
        <div className="animate-fade">
          {eliminatedCount > 0 && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
              <AlertTriangle className="text-red-600 mt-0.5 shrink-0" size={20}/>
              <div>
                <p className="font-bold text-red-800">Attention : Élimination dans {eliminatedCount} matière(s)</p>
                <p className="text-xs text-red-600 mt-1">Plus de 3 absences entraîne l'élimination automatique de la matière.</p>
              </div>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {absences.map((a,i) => (
              <div key={i} className={`glass-card flex items-center justify-between ${a.eliminated ? 'border-l-4 border-red-500' : a.absences > 2 ? 'border-l-4 border-amber-400' : ''}`}>
                <div>
                  <p className="font-bold text-slate-800 text-sm">{a.subject}</p>
                  <p className="text-xs text-slate-500 mt-1">Limite : {a.limit} absences</p>
                </div>
                <div className="text-right">
                  <span className={`text-2xl font-extrabold ${a.eliminated ? 'text-red-600' : a.absences > 2 ? 'text-amber-600' : 'text-emerald-600'}`}>{a.absences}</span>
                  {a.eliminated && <p className="text-xs font-bold text-red-600 mt-1">ÉLIMINÉ</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Demandes */}
      {activeTab === 'demandes' && (
        <div className="animate-fade">
          <div className="glass-card mb-6">
            <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2"><Send size={20} className="text-amber-600"/> Nouvelle demande</h3>
            {reqMsg && <div className="mb-4 px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm font-bold text-sm animate-fade">{reqMsg}</div>}
            <div className="flex flex-col sm:flex-row gap-3">
              <select value={newReq.type} onChange={e => setNewReq({...newReq, type: e.target.value})} className="form-input flex-1">
                {REQUEST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <input value={newReq.message} onChange={e => setNewReq({...newReq, message: e.target.value})} placeholder="Message (optionnel)" className="form-input flex-1"/>
              <button onClick={handleSubmitRequest} className="px-6 py-2.5 bg-amber-600 text-white rounded-xl font-bold text-sm hover:bg-amber-700 transition-all shadow-lg shadow-amber-600/20 flex items-center gap-2 shrink-0">
                <Send size={16}/> Envoyer
              </button>
            </div>
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-4">Historique des demandes</h3>
          {requests.length === 0 ? (
            <div className="glass-card text-center py-12"><FileText size={40} className="mx-auto text-slate-300 mb-3"/><p className="text-slate-500 font-medium">Aucune demande pour le moment</p></div>
          ) : (
            <div className="space-y-3">
              {requests.map((r,i) => (
                <div key={i} className="glass-card flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-xl ${r.status === 'approved' ? 'bg-emerald-100 text-emerald-600' : r.status === 'rejected' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
                      {r.status === 'approved' ? <CheckCircle size={20}/> : r.status === 'rejected' ? <XCircle size={20}/> : <Clock size={20}/>}
                    </div>
                    <div>
                      <p className="font-bold text-slate-800">{r.type}</p>
                      {r.message && <p className="text-xs text-slate-500 mt-1">{r.message}</p>}
                      {r.admin_response && <p className="text-xs text-slate-600 mt-2 bg-slate-50 p-2 rounded font-medium">Réponse : {r.admin_response}</p>}
                      <p className="text-xs text-slate-400 mt-1">{r.created_at ? new Date(r.created_at).toLocaleDateString('fr-FR') : ''}</p>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold shrink-0 ${r.status === 'approved' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : r.status === 'rejected' ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-amber-50 text-amber-700 border border-amber-100'}`}>
                    {r.status === 'approved' ? 'Approuvée' : r.status === 'rejected' ? 'Refusée' : 'En attente'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Vie Associative */}
      {activeTab === 'events' && (
        <div className="animate-fade">
          <div className="glass-card mb-6">
            <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2"><PlusCircle size={20} className="text-pink-600"/> Proposer un Événement</h3>
            {eventMsg && <div className="mb-4 px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm font-bold text-sm animate-fade">{eventMsg}</div>}
            <div className="flex flex-col gap-4">
              <div className="flex flex-col sm:flex-row gap-3">
                <input value={newEvent.title} onChange={e => setNewEvent({...newEvent, title: e.target.value})} placeholder="Titre de l'événement *" className="form-input flex-1" />
                <input value={newEvent.club} onChange={e => setNewEvent({...newEvent, club: e.target.value})} placeholder="Nom du Club / Association *" className="form-input flex-1" />
                <input type="date" value={newEvent.date} onChange={e => setNewEvent({...newEvent, date: e.target.value})} className="form-input flex-1" />
              </div>
              <div className="flex flex-col sm:flex-row gap-3 items-end">
                <input value={newEvent.description} onChange={e => setNewEvent({...newEvent, description: e.target.value})} placeholder="Description de l'événement (Objectifs, lieu attendu...)" className="form-input flex-1" />
                <button onClick={handleSubmitEvent} className="px-6 py-2.5 bg-pink-600 text-white rounded-xl font-bold text-sm hover:bg-pink-700 transition-all shadow-lg shadow-pink-600/20 flex items-center gap-2 shrink-0">
                  <Send size={16}/> Soumettre
                </button>
              </div>
            </div>
          </div>

          <h3 className="text-lg font-bold text-slate-800 mb-4">Événements Proposés</h3>
          {events.length === 0 ? (
            <div className="glass-card text-center py-12"><Users size={40} className="mx-auto text-slate-300 mb-3"/><p className="text-slate-500 font-medium">Aucun événement proposé pour le moment</p></div>
          ) : (
            <div className="space-y-3">
              {events.map((ev, i) => (
                <div key={i} className="glass-card flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-xl ${ev.status === 'approved' ? 'bg-emerald-100 text-emerald-600' : ev.status === 'rejected' ? 'bg-red-100 text-red-600' : 'bg-pink-100 text-pink-600'}`}>
                      {ev.status === 'approved' ? <CheckCircle size={20}/> : ev.status === 'rejected' ? <XCircle size={20}/> : <Clock size={20}/>}
                    </div>
                    <div>
                      <p className="font-bold text-slate-800">{ev.title} <span className="text-pink-600 ml-2">({ev.club})</span></p>
                      <p className="text-xs font-semibold text-slate-500 mt-1">Prévu pour le : {ev.date ? new Date(ev.date).toLocaleDateString('fr-FR') : ''}</p>
                      {ev.description && <p className="text-xs text-slate-600 mt-2">{ev.description}</p>}
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold shrink-0 ${ev.status === 'approved' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : ev.status === 'rejected' ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-pink-50 text-pink-700 border border-pink-100'}`}>
                    {ev.status === 'approved' ? 'Approuvé' : ev.status === 'rejected' ? 'Refusé' : 'En attente'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Notifications */}
      {activeTab === 'notifications' && (
        <div className="animate-fade">
          {notifications.length === 0 ? (
            <div className="glass-card text-center py-16"><Bell size={40} className="mx-auto text-slate-300 mb-3"/><p className="text-slate-500 font-medium">Aucune notification</p></div>
          ) : (
            <div className="space-y-3">
              {notifications.map((n,i) => (
                <div key={i} className={`glass-card flex items-start justify-between gap-4 transition-all ${!n.read ? 'border-l-4 border-amber-500 bg-amber-50/30' : ''}`} onClick={() => !n.read && markRead(n.id)} style={{cursor: !n.read ? 'pointer' : 'default'}}>
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-xl ${n.type === 'grade' ? 'bg-blue-100 text-blue-600' : n.type === 'warning' ? 'bg-red-100 text-red-600' : n.type === 'request_status' ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-600'}`}>
                      {n.type === 'grade' ? <Award size={20}/> : n.type === 'warning' ? <AlertTriangle size={20}/> : n.type === 'request_status' ? <CheckCircle size={20}/> : <Bell size={20}/>}
                    </div>
                    <div>
                      <p className={`font-bold text-slate-800 ${!n.read ? '' : 'opacity-70'}`}>{n.title}</p>
                      <p className="text-xs text-slate-500 mt-1">{n.message}</p>
                      <p className="text-xs text-slate-400 mt-1">{n.created_at ? new Date(n.created_at).toLocaleDateString('fr-FR', {hour: '2-digit', minute: '2-digit'}) : ''}</p>
                    </div>
                  </div>
                  {!n.read && <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0 mt-2"/>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
