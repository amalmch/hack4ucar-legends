import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../api';
import StatCard from '../../components/StatCard';
import { Users, BookOpen, FileText, TrendingUp, Upload, Search, Download, CheckCircle, XCircle, Clock } from 'lucide-react';

import { exportToPDF } from '../../utils/pdfExport';
import AIInsightsPanel from '../../components/AIInsightsPanel';
import IngestionPanel from '../../components/IngestionPanel';

export default function InstitutionDashboard() {
  const [overview, setOverview] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [docs, setDocs] = useState([]);
  const [requests, setRequests] = useState([]);
  const [events, setEvents] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const [searchParams] = useSearchParams();
  const instIdParam = searchParams.get('id');

  useEffect(() => {
    async function load() {
      try {
        const query = instIdParam ? `?institution_id=${instIdParam}` : '';
        const qChar = instIdParam ? '&' : '?';

        const [ovRes, stuRes, tchRes, docRes, reqRes, evRes] = await Promise.all([
          api.get(`/api/institution/overview${query}`),
          api.get(`/api/institution/students${query ? query + '&' : '?'}per_page=100`),
          api.get(`/api/institution/teachers${query}`),
          api.get(`/api/institution/documents${query}`),
          api.get(`/api/institution/requests${query}`),
          api.get(`/api/institution/events${query}`),
        ]);
        setOverview(ovRes.data);
        setStudents(stuRes.data.students || []);
        setTeachers(tchRes.data.teachers || []);
        setDocs(docRes.data.documents || []);
        setRequests(reqRes.data.requests || []);
        setEvents(evRes.data.events || []);
      } catch (e) { console.error(e); }
      setLoading(false);
    }
    load();
  }, [instIdParam]);

  const handleExport = async () => {
    setExporting(true);
    await exportToPDF('institution-dashboard-content', `Rapport_${overview?.institution?.id || 'Etablissement'}.pdf`);
    setExporting(false);
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('document', file);
    fd.append('type', 'institutional');
    fd.append('description', file.name);
    if (instIdParam) fd.append('institution_id', instIdParam);
    await api.post('/api/institution/documents/upload', fd);
    const query = instIdParam ? `?institution_id=${instIdParam}` : '';
    const res = await api.get(`/api/institution/documents${query}`);
    setDocs(res.data.documents || []);
  };

  const handleRequestAction = async (id, action) => {
    try {
      await api.post(`/api/institution/requests/${id}/${action}`);
      const query = instIdParam ? `?institution_id=${instIdParam}` : '';
      const reqRes = await api.get(`/api/institution/requests${query}`);
      setRequests(reqRes.data.requests || []);
    } catch (e) { console.error(e); }
  };

  const handleEventAction = async (id, action) => {
    try {
      await api.post(`/api/institution/events/${id}/${action}`);
      const query = instIdParam ? `?institution_id=${instIdParam}` : '';
      const evRes = await api.get(`/api/institution/events${query}`);
      setEvents(evRes.data.events || []);
    } catch (e) { console.error(e); }
  };

  const handleAssignStudentClass = async (studentId, currentClass) => {
    const newClass = prompt("Entrez la classe (ex: GL3, 1A) :", currentClass || "");
    if (newClass !== null) {
      try {
        await api.put(`/api/institution/students/${studentId}/classe`, { classe: newClass });
        const query = instIdParam ? `?institution_id=${instIdParam}` : '';
        const stuRes = await api.get(`/api/institution/students${query ? query + '&' : '?'}per_page=100`);
        setStudents(stuRes.data.students || []);
      } catch (e) { alert("Erreur lors de l'assignation de la classe"); }
    }
  };

  const handleAssignTeacherClasses = async (teacherId, currentClasses) => {
    const newClasses = prompt("Entrez les classes (séparées par virgules, ex: GL3, RT4) :", (currentClasses || []).join(", "));
    if (newClasses !== null) {
      try {
        await api.put(`/api/institution/teachers/${teacherId}/classes`, { classes: newClasses });
        const query = instIdParam ? `?institution_id=${instIdParam}` : '';
        const tchRes = await api.get(`/api/institution/teachers${query}`);
        setTeachers(tchRes.data.teachers || []);
      } catch (e) { alert("Erreur lors de l'assignation des classes"); }
    }
  };

  const filteredStudents = students.filter(s =>
    !search || `${s.nom} ${s.prenom} ${s.student_id} ${s.classe || ''}`.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          <p className="font-medium">Chargement des données de l'établissement...</p>
        </div>
      </div>
    );
  }

  const tabs = ['overview', 'ingestion', 'students', 'teachers', 'documents', 'approvals'];

  const pendingCount = requests.filter(r => r.status === 'pending').length + events.filter(e => e.status === 'pending').length;

  return (
    <div id="institution-dashboard-content" className="animate-fade max-w-7xl mx-auto pb-10 bg-slate-50">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-bold uppercase tracking-wider border border-indigo-100 shadow-sm">
              Admin Établissement
            </span>
            <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-xs font-bold uppercase tracking-wider border border-slate-200 shadow-sm">
              {overview?.institution?.id || 'UCAR'}
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-slate-900 mb-1 tracking-tight">
            {overview?.institution?.name || 'Gestion de l\'Établissement'}
          </h1>
          <p className="text-slate-500 font-medium text-sm sm:text-base">
            Données académiques, financières et administratives en temps réel
          </p>
        </div>
        <button 
          onClick={handleExport}
          disabled={exporting}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-700 hover:bg-slate-50 shadow-sm transition-all group disabled:opacity-50"
        >
          {exporting ? (
            <span className="w-4 h-4 border-2 border-slate-300 border-t-indigo-600 rounded-full animate-spin"></span>
          ) : (
            <Download size={16} className="text-slate-400 group-hover:text-indigo-600" />
          )}
          {exporting ? 'Exportation...' : 'Exporter le Rapport'}
        </button>
      </header>

      <AIInsightsPanel />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 animate-fade">
        <StatCard title="Étudiants" value={overview?.students_total || students.length} icon={Users} />
        <StatCard title="Enseignants" value={overview?.teachers_total || teachers.length} icon={BookOpen} />
        <StatCard title="Documents" value={overview?.documents_total || docs.length} icon={FileText} />
        <StatCard title="Rapports IA" value={overview?.reports_total || 0} icon={TrendingUp} />
      </div>

      {/* Tabs Navigation */}
      <div className="flex gap-2 sm:gap-6 mb-8 border-b border-slate-200 overflow-x-auto no-scrollbar">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`whitespace-nowrap px-4 py-4 border-b-2 font-bold text-sm transition-all duration-300 ${
              activeTab === t 
                ? 'border-indigo-600 text-indigo-700' 
                : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
            }`}
          >
            {t === 'overview' ? 'Vue globale'
              : t === 'ingestion' ? '📥 Ingestion'
              : t === 'students' ? `Étudiants (${students.length})` 
              : t === 'teachers' ? `Enseignants (${teachers.length})` 
              : t === 'documents' ? `Documents (${docs.length})`
              : <span className="flex items-center gap-2">Approbations {pendingCount > 0 && <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs">{pendingCount}</span>}</span>
            }
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {activeTab === 'overview' && overview && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade">
          <div className="glass-card">
            <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-3">
              <div className="w-2 h-6 bg-indigo-500 rounded-full" />
              Indicateurs Clés de Performance (KPIs)
            </h3>
            <div className="space-y-1">
              {overview.latest_kpis && Object.keys(overview.latest_kpis)
                .filter(k => !['institution_id','institution_name','date','annee_reference','ville'].includes(k))
                .slice(0, 8)
                .map(k => (
                <div key={k} className="flex justify-between items-center py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50 px-2 rounded-lg transition-colors">
                  <span className="text-sm font-medium text-slate-600 capitalize">{k.replace(/_/g, ' ')}</span>
                  <strong className="text-slate-900">
                    {typeof overview.latest_kpis[k] === 'number' 
                      ? overview.latest_kpis[k].toLocaleString('fr-FR', { maximumFractionDigits: 2 }) 
                      : overview.latest_kpis[k]}
                  </strong>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card">
            <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-3">
              <div className="w-2 h-6 bg-emerald-500 rounded-full" />
              Impact Environnemental (ESG)
            </h3>
            <div className="flex flex-col gap-3">
              {[
                { label: 'Empreinte Carbone', value: overview.latest_kpis?.empreinte_carbone_tonnes ? `${overview.latest_kpis.empreinte_carbone_tonnes} T` : 'N/A', icon: '🌍' },
                { label: 'Consommation Énergie', value: overview.latest_kpis?.consommation_energie_kwh ? `${(overview.latest_kpis.consommation_energie_kwh / 1000).toFixed(1)} MWh` : 'N/A', icon: '⚡' },
                { label: 'Taux de Recyclage', value: overview.latest_kpis?.taux_recyclage ? `${(overview.latest_kpis.taux_recyclage * 100).toFixed(1)}%` : 'N/A', icon: '♻️' },
                { label: 'Coût par étudiant', value: overview.latest_kpis?.cout_par_etudiant ? `${overview.latest_kpis.cout_par_etudiant} TND` : 'N/A', icon: '💰' },
              ].map((r, i) => (
                <div key={i} className="flex justify-between items-center p-4 bg-slate-50 border border-slate-100 rounded-xl hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{r.icon}</span>
                    <span className="text-sm font-bold text-slate-700">{r.label}</span>
                  </div>
                  <strong className="text-lg font-extrabold text-emerald-700">{r.value}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Ingestion */}
      {activeTab === 'ingestion' && (
        <div className="animate-fade">
          <IngestionPanel institutionId={overview?.institution_id} />
        </div>
      )}

      {/* Tab: Students */}
      {activeTab === 'students' && (
        <div className="animate-fade">
          <div className="mb-6 relative max-w-md">
            <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              value={search} 
              onChange={e => setSearch(e.target.value)} 
              placeholder="Rechercher un étudiant par nom, prénom ou ID..." 
              className="form-input w-full pl-12" 
            />
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Étudiant</th>
                  <th>Programme</th>
                  <th>Niveau</th>
                  <th>Classe</th>
                  <th>Moy. S1</th>
                  <th>Absences</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.slice(0, 100).map((s, i) => (
                  <tr key={i} className="group">
                    <td>
                      <p className="font-bold text-slate-800">{s.prenom} {s.nom}</p>
                      <p className="text-xs font-mono text-slate-400 mt-0.5">{s.student_id}</p>
                    </td>
                    <td className="text-sm text-slate-600 font-medium max-w-[200px] truncate" title={s.programme}>{s.programme}</td>
                    <td>
                      <span className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded-md text-xs font-bold border border-blue-100">
                        {s.niveau}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        {s.classe ? (
                          <span className="font-bold text-slate-800">{s.classe}</span>
                        ) : (
                          <span className="text-xs italic text-slate-400">Non assigné</span>
                        )}
                        <button 
                          onClick={() => handleAssignStudentClass(s.student_id, s.classe)}
                          className="text-xs text-indigo-600 hover:text-indigo-800 underline"
                        >
                          Éditer
                        </button>
                      </div>
                    </td>
                    <td className={`font-bold ${s.moyenne_s1 < 10 ? 'text-red-600' : 'text-slate-700'}`}>
                      {s.moyenne_s1}
                    </td>
                    <td className={`font-semibold ${s.nb_absences_s1 > 10 ? 'text-amber-600' : 'text-slate-600'}`}>
                      {s.nb_absences_s1}
                    </td>
                    <td>
                      <span className={`px-2.5 py-1 rounded-md text-xs font-bold border ${
                        s.statut === 'abandonne' ? 'bg-red-50 text-red-700 border-red-100' : 
                        s.statut === 'diplome' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 
                        'bg-slate-100 text-slate-600 border-slate-200'
                      }`}>
                        {s.statut}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredStudents.length === 0 && (
              <div className="p-8 text-center text-slate-500 font-medium">Aucun étudiant trouvé.</div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Teachers */}
      {activeTab === 'teachers' && (
        <div className="table-container animate-fade">
          <table>
            <thead>
              <tr>
                <th>Enseignant</th>
                <th>Département</th>
                <th>Classes</th>
                <th>Heures/an</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {teachers.map((t, i) => (
                <tr key={i}>
                  <td>
                    <p className="font-bold text-slate-800">{t.prenom} {t.nom}</p>
                    <p className="text-xs text-slate-500 font-medium">{t.grade}</p>
                  </td>
                  <td className="text-sm text-slate-600 font-medium">{t.departement}</td>
                  <td>
                    <div className="flex items-center gap-2 flex-wrap">
                      {t.classes_enseignees && t.classes_enseignees.length > 0 ? (
                        t.classes_enseignees.map((c, idx) => (
                          <span key={idx} className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-bold border border-indigo-100">{c}</span>
                        ))
                      ) : (
                        <span className="text-xs italic text-slate-400">Aucune</span>
                      )}
                      <button 
                        onClick={() => handleAssignTeacherClasses(t.teacher_id, t.classes_enseignees)}
                        className="text-xs text-indigo-600 hover:text-indigo-800 underline ml-2"
                      >
                        Éditer
                      </button>
                    </div>
                  </td>
                  <td className={`font-bold ${t.nb_heures_cours_annee > 300 ? 'text-amber-600' : 'text-slate-700'}`}>
                    {t.nb_heures_cours_annee}h
                  </td>
                  <td>
                    <span className={`px-2.5 py-1 rounded-md text-xs font-bold border ${
                      t.statut === 'Permanent' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 
                      'bg-amber-50 text-amber-700 border-amber-100'
                    }`}>
                      {t.statut}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Documents */}
      {activeTab === 'documents' && (
        <div className="animate-fade">
          <div className="mb-6">
            <label htmlFor="doc-up" className="inline-flex items-center gap-2 px-6 py-3 bg-accent-gradient text-white rounded-xl cursor-pointer font-bold shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all group">
              <Upload size={18} className="group-hover:-translate-y-1 transition-transform" /> 
              Importer un nouveau document
              <input id="doc-up" type="file" onChange={handleUpload} className="hidden" />
            </label>
          </div>
          
          {docs.length === 0 ? (
            <div className="glass-card flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 bg-slate-100 text-slate-400 rounded-2xl flex items-center justify-center mb-4">
                <FileText size={32} />
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-1">Aucun document</h3>
              <p className="text-slate-500 font-medium text-sm">Importez votre premier fichier pour commencer.</p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Fichier</th>
                    <th>Type</th>
                    <th>Taille</th>
                    <th>Importé le</th>
                    <th>Par</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((d, i) => (
                    <tr key={i}>
                      <td className="font-bold text-slate-800 flex items-center gap-3">
                        <FileText size={16} className="text-slate-400" />
                        {d.filename || d.description || 'Document'}
                      </td>
                      <td>
                        <span className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded-md text-xs font-bold border border-blue-100">
                          {d.type}
                        </span>
                      </td>
                      <td className="text-sm font-medium text-slate-500">
                        {d.size_bytes ? `${(d.size_bytes / 1024).toFixed(1)} KB` : '-'}
                      </td>
                      <td className="text-sm font-medium text-slate-500">
                        {d.uploaded_at ? new Date(d.uploaded_at).toLocaleDateString('fr-FR') : '-'}
                      </td>
                      <td className="text-sm font-medium text-slate-500">
                        {d.uploaded_by || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Approvals */}
      {activeTab === 'approvals' && (
        <div className="animate-fade grid grid-cols-1 xl:grid-cols-2 gap-8">
          <div>
            <h3 className="text-xl font-bold text-slate-800 mb-6 border-b border-slate-200 pb-2">Demandes Administratives</h3>
            {requests.length === 0 ? (
              <div className="p-8 text-center text-slate-500 font-medium glass-card">Aucune demande</div>
            ) : (
              <div className="space-y-4">
                {requests.map((r, i) => (
                  <div key={i} className="glass-card p-5">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="font-bold text-slate-800 text-lg">{r.type}</p>
                        <p className="text-sm font-medium text-slate-500">Étudiant ID: {r.student_id}</p>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${r.status === 'approved' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : r.status === 'rejected' ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-amber-50 text-amber-700 border border-amber-100'}`}>
                        {r.status === 'approved' ? 'Approuvée' : r.status === 'rejected' ? 'Refusée' : 'En attente'}
                      </span>
                    </div>
                    {r.message && <p className="text-sm text-slate-600 mb-3 bg-slate-50 p-2 rounded">{r.message}</p>}
                    <p className="text-xs text-slate-400 mb-4">{new Date(r.created_at).toLocaleString('fr-FR')}</p>
                    
                    {r.status === 'pending' && (
                      <div className="flex gap-2">
                        <button onClick={() => handleRequestAction(r.id, 'approve')} className="flex-1 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg font-bold text-sm transition-colors border border-emerald-200">Approuver</button>
                        <button onClick={() => handleRequestAction(r.id, 'reject')} className="flex-1 py-2 bg-red-50 text-red-700 hover:bg-red-100 rounded-lg font-bold text-sm transition-colors border border-red-200">Refuser</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <h3 className="text-xl font-bold text-slate-800 mb-6 border-b border-slate-200 pb-2">Vie Associative (Événements)</h3>
            {events.length === 0 ? (
              <div className="p-8 text-center text-slate-500 font-medium glass-card">Aucun événement</div>
            ) : (
              <div className="space-y-4">
                {events.map((ev, i) => (
                  <div key={i} className="glass-card p-5">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="font-bold text-slate-800 text-lg">{ev.title}</p>
                        <p className="text-sm font-medium text-pink-600 flex items-center gap-2">
                          <Users size={16} /> Club: {ev.club}
                        </p>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${ev.status === 'approved' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : ev.status === 'rejected' ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-pink-50 text-pink-700 border border-pink-100'}`}>
                        {ev.status === 'approved' ? 'Approuvé' : ev.status === 'rejected' ? 'Refusé' : 'En attente'}
                      </span>
                    </div>
                    <p className="text-sm font-bold text-slate-700 mb-1">Prévu le : {new Date(ev.date).toLocaleDateString('fr-FR')}</p>
                    {ev.description && <p className="text-sm text-slate-600 mb-3 bg-slate-50 p-2 rounded">{ev.description}</p>}
                    <p className="text-xs text-slate-400 mb-4">Proposé par (ID): {ev.student_id}</p>
                    
                    {ev.status === 'pending' && (
                      <div className="flex gap-2">
                        <button onClick={() => handleEventAction(ev.id, 'approve')} className="flex-1 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg font-bold text-sm transition-colors border border-emerald-200">Autoriser</button>
                        <button onClick={() => handleEventAction(ev.id, 'reject')} className="flex-1 py-2 bg-red-50 text-red-700 hover:bg-red-100 rounded-lg font-bold text-sm transition-colors border border-red-200">Refuser</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
