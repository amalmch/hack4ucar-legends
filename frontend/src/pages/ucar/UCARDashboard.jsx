import React, { useState, useEffect } from 'react';
import api from '../../api';
import StatCard from '../../components/StatCard';
import { Users, Building2, Clock, Activity, CheckCircle, XCircle, Download, ExternalLink, Globe, List, Award, GraduationCap, Briefcase, Landmark, Leaf, Users2, Microscope, Building, Handshake, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { exportToPDF } from '../../utils/pdfExport';
import AIInsightsPanel from '../../components/AIInsightsPanel';
import IngestionPanel from '../../components/IngestionPanel';
import DigitalTwin from '../../components/DigitalTwin';

export default function UCARDashboard() {
  const [overview, setOverview] = useState(null);
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [instViewMode, setInstViewMode] = useState('3d'); // '3d' or 'list'
  const [actionMsg, setActionMsg] = useState('');
  const [exporting, setExporting] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const [ovRes, pendRes] = await Promise.all([
        api.get('/api/ucar/overview'),
        api.get('/api/ucar/users/pending'),
      ]);
      setOverview(ovRes.data);
      setPending(pendRes.data.pending_users || []);
    } catch (e) { console.error('UCAR dashboard error:', e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleExport = async () => {
    setExporting(true);
    await exportToPDF('ucar-dashboard-content', 'Rapport_UCAR_HQ.pdf');
    setExporting(false);
  };

  const handleApprove = async (userId) => {
    await api.post(`/api/ucar/users/${userId}/approve`);
    setActionMsg('✅ Compte approuvé !');
    load();
    setTimeout(() => setActionMsg(''), 3000);
  };

  const handleReject = async (userId) => {
    const reason = window.prompt('Raison du refus:') || 'Document non conforme';
    if (!reason) return;
    await api.post(`/api/ucar/users/${userId}/reject`, { reason });
    setActionMsg('❌ Compte refusé.');
    load();
    setTimeout(() => setActionMsg(''), 3000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-ucar-200 border-t-ucar-600 rounded-full animate-spin" />
          <p className="font-medium">Chargement du tableau de bord UCAR...</p>
        </div>
      </div>
    );
  }

  const summary = overview?.summary || {};
  const institutions = overview?.institutions || [];

  const chartData = institutions
    .filter(i => i.students > 0)
    .sort((a, b) => b.students - a.students)
    .slice(0, 10)
    .map(i => ({
      name: i.id.replace('UCAR-', ''),
      students: i.students,
      teachers: i.teachers,
    }));

  const tabs = ['overview', 'ingestion', 'institutions', 'approvals'];

  return (
    <div id="ucar-dashboard-content" className="animate-fade max-w-7xl mx-auto pb-10 bg-slate-50">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="px-3 py-1 bg-ucar-50 text-ucar-700 rounded-full text-xs font-bold uppercase tracking-wider border border-ucar-100 shadow-sm">
              UCAR HQ
            </span>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold uppercase tracking-wider border border-emerald-100 shadow-sm">
              Super Admin
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-slate-900 mb-1 tracking-tight">Tableau de Bord Global</h1>
          <p className="text-slate-500 font-medium text-sm sm:text-base">
            Vue consolidée — {summary.total_institutions || 32} établissements affiliés
          </p>
        </div>
        <div className="flex items-center gap-4">
          {actionMsg && (
            <div className="animate-slide-in-right px-5 py-3 bg-white border border-slate-200 shadow-lg shadow-slate-200/50 rounded-xl font-bold text-slate-800 flex items-center gap-3">
              {actionMsg}
            </div>
          )}
          <button 
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-3 bg-white border border-slate-200 rounded-xl text-sm font-bold text-slate-700 hover:bg-slate-50 shadow-sm transition-all group disabled:opacity-50"
          >
            {exporting ? (
              <span className="w-4 h-4 border-2 border-slate-300 border-t-ucar-600 rounded-full animate-spin"></span>
            ) : (
              <Download size={16} className="text-slate-400 group-hover:text-ucar-600" />
            )}
            {exporting ? 'Exportation...' : 'Exporter le Rapport'}
          </button>
        </div>
      </header>

      <AIInsightsPanel />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 animate-fade">
        <StatCard title="Établissements" value={summary.total_institutions || 32} icon={Building2} />
        <StatCard title="Étudiants" value={(summary.total_students || 0).toLocaleString()} icon={Users} trend="+8%" />
        <StatCard title="Enseignants" value={(summary.total_teachers || 0).toLocaleString()} icon={Activity} />
        <StatCard
          title="Comptes en Attente"
          value={pending.length}
          icon={Clock}
          alert={pending.length > 0}
        />
      </div>

      {/* Tabs Navigation */}
      <div className="flex gap-2 sm:gap-6 mb-8 border-b border-slate-200 overflow-x-auto no-scrollbar">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`whitespace-nowrap px-4 py-4 border-b-2 font-bold text-sm transition-all duration-300 ${
              activeTab === t 
                ? 'border-ucar-600 text-ucar-700' 
                : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
            }`}
          >
            {t === 'overview' ? 'Vue Globale'
              : t === 'ingestion' ? '📥 Ingestion Données'
              : t === 'institutions' ? `Établissements (${institutions.length})`
              : (
                  <span className="flex items-center gap-2">
                    Approbations
                    {pending.length > 0 && (
                      <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs">
                        {pending.length}
                      </span>
                    )}
                  </span>
                )
            }
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="flex flex-col gap-6 animate-fade">
          
          {/* UCAR RANKING PRESTIGE CARD */}
          <div className="w-full rounded-2xl overflow-hidden shadow-lg border border-yellow-200/50 relative group">
            <div className="absolute inset-0 bg-gradient-to-r from-ucar-900 via-blue-900 to-indigo-900"></div>
            <div className="absolute inset-0 opacity-20 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-yellow-300 via-transparent to-transparent"></div>
            
            <div className="relative p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-5">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-yellow-300 to-yellow-600 flex items-center justify-center shadow-inner shadow-yellow-200/50 shrink-0">
                  <Award size={32} className="text-white drop-shadow-md" />
                </div>
                <div>
                  <h2 className="text-2xl font-black text-white tracking-tight mb-1">Université de Carthage (UCAR)</h2>
                  <p className="text-blue-200 font-medium text-sm flex items-center gap-2">
                    <Globe size={14} /> Consolidation Globale • 33 Établissements Partenaires
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4 w-full md:w-auto">
                <div className="flex-1 md:flex-none bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/10 text-center">
                  <div className="text-xs font-bold text-yellow-400 uppercase tracking-widest mb-1">Classement National</div>
                  <div className="text-3xl font-black text-white">#1</div>
                  <div className="text-[10px] text-blue-200 mt-1">Tunisie 🇹🇳</div>
                </div>
                <div className="flex-1 md:flex-none bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/10 text-center">
                  <div className="text-xs font-bold text-blue-300 uppercase tracking-widest mb-1">Classement Mondial</div>
                  <div className="text-3xl font-black text-white">#801<span className="text-lg text-blue-200 font-bold">-1000</span></div>
                  <div className="text-[10px] text-blue-200 mt-1">QS World University Rankings</div>
                </div>
              </div>
            </div>
          </div>
          {chartData.length > 0 && (
            <div className="glass-card w-full">
              <h2 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-3">
                <div className="w-2 h-6 bg-ucar-500 rounded-full" />
                Répartition des Étudiants — Top 10 Établissements
              </h2>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b', fontWeight: 500 }} axisLine={false} tickLine={false} dy={10} />
                    <YAxis tick={{ fontSize: 12, fill: '#64748b', fontWeight: 500 }} axisLine={false} tickLine={false} dx={-10} />
                    <Tooltip 
                      cursor={{ fill: '#f8fafc' }}
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 25px rgba(0,0,0,0.05)', fontWeight: 600 }} 
                    />
                    <Bar dataKey="students" name="Étudiants" radius={[6, 6, 0, 0]} maxBarSize={60}>
                      {chartData.map((_, i) => (
                        <Cell key={i} fill={`hsl(220, 70%, ${58 - i * 2}%)`} className="hover:opacity-80 transition-opacity cursor-pointer" />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* DOMAINS STRATEGIC GRID */}
          <div className="mt-4">
            <h2 className="text-xl font-bold text-slate-800 mb-6 flex items-center gap-3">
              <div className="w-2 h-6 bg-ucar-500 rounded-full" />
              Indicateurs Stratégiques par Domaine
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              
              {/* 1. Académique */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                    <GraduationCap size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">Académique</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Taux de réussite</span><span className="font-bold text-slate-700">78.4%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Taux d'abandon</span><span className="font-bold text-amber-600">4.2%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Progression pédag.</span><span className="font-bold text-slate-700">82%</span></li>
                </ul>
              </div>

              {/* 2. Employabilité */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                    <Briefcase size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">Employabilité</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Taux d'emploi (6 mois)</span><span className="font-bold text-emerald-600">85.1%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Délai moyen d'embauche</span><span className="font-bold text-slate-700">2.4 mois</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Partenariats entreprises</span><span className="font-bold text-slate-700">142</span></li>
                </ul>
              </div>

              {/* 3. Finance */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-amber-50 text-amber-600 group-hover:bg-amber-600 group-hover:text-white transition-colors">
                    <Landmark size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">Finance</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Budget exécuté</span><span className="font-bold text-slate-700">92.5%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Coût par étudiant</span><span className="font-bold text-slate-700">3 450 TND</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Financements externes</span><span className="font-bold text-emerald-600">+12%</span></li>
                </ul>
              </div>

              {/* 4. ESG / RSE */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-teal-50 text-teal-600 group-hover:bg-teal-600 group-hover:text-white transition-colors">
                    <Leaf size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">ESG / RSE</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Empreinte carbone</span><span className="font-bold text-emerald-600">-5.2%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Taux de recyclage</span><span className="font-bold text-slate-700">41%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Mobilité durable</span><span className="font-bold text-slate-700">28%</span></li>
                </ul>
              </div>

              {/* 5. RH */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                    <Users2 size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">RH</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Effectif total (Ens/Adm)</span><span className="font-bold text-slate-700">4 250</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Taux d'absentéisme</span><span className="font-bold text-slate-700">2.1%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Stabilité équipes</span><span className="font-bold text-emerald-600">94%</span></li>
                </ul>
              </div>

              {/* 6. Recherche */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-purple-50 text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                    <Microscope size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">Recherche</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Publications (A/A+)</span><span className="font-bold text-slate-700">1 240</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Brevets déposés</span><span className="font-bold text-emerald-600">18</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Projets actifs</span><span className="font-bold text-slate-700">86</span></li>
                </ul>
              </div>

              {/* 7. Infrastructure */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-orange-50 text-orange-600 group-hover:bg-orange-600 group-hover:text-white transition-colors">
                    <Building size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">Infrastructure</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Taux occupation salles</span><span className="font-bold text-slate-700">72%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Statut parc IT</span><span className="font-bold text-emerald-600">Opérationnel</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Travaux en cours</span><span className="font-bold text-amber-600">3 chantiers</span></li>
                </ul>
              </div>

              {/* 8. Partenariats */}
              <div className="glass-card hover:-translate-y-1 transition-transform duration-300 group">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 rounded-lg bg-rose-50 text-rose-600 group-hover:bg-rose-600 group-hover:text-white transition-colors">
                    <Handshake size={20} />
                  </div>
                  <h3 className="font-bold text-slate-800">Partenariats</h3>
                </div>
                <ul className="space-y-3 text-sm">
                  <li className="flex justify-between items-center"><span className="text-slate-500">Accords actifs</span><span className="font-bold text-slate-700">215</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Mobilité sortante</span><span className="font-bold text-emerald-600">+8%</span></li>
                  <li className="flex justify-between items-center"><span className="text-slate-500">Mobilité entrante</span><span className="font-bold text-slate-700">450 étud.</span></li>
                </ul>
              </div>

            </div>
          </div>
        </div>
      )}

      {/* Ingestion Tab */}
      {activeTab === 'ingestion' && (
        <div className="animate-fade">
          <IngestionPanel />
        </div>
      )}

      {/* Institutions Tab */}
      {activeTab === 'institutions' && (
        <div className="animate-fade">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-slate-800">Établissements UCAR</h2>
            <div className="flex bg-slate-100 p-1 rounded-xl shadow-inner border border-slate-200">
              <button 
                onClick={() => setInstViewMode('3d')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm transition-all ${
                  instViewMode === '3d' ? 'bg-white text-ucar-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <Globe size={16} /> Vue 3D Metaverse
              </button>
              <button 
                onClick={() => setInstViewMode('list')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm transition-all ${
                  instViewMode === 'list' ? 'bg-white text-ucar-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <List size={16} /> Vue Liste
              </button>
            </div>
          </div>

          {instViewMode === '3d' ? (
            <DigitalTwin />
          ) : (
            <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Établissement</th>
                <th>Ville</th>
                <th>Étudiants</th>
                <th>Enseignants</th>
                <th>Données</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {institutions.map(inst => (
                <tr key={inst.id} className="group hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => navigate(`/institution?id=${inst.id}`)}>
                  <td className="text-xs font-mono text-slate-400 group-hover:text-ucar-500 transition-colors">{inst.id}</td>
                  <td className="font-bold text-slate-800 max-w-xs truncate">{inst.name}</td>
                  <td className="text-slate-500 font-medium">{inst.city}</td>
                  <td className="font-semibold text-slate-700">{(inst.students || 0).toLocaleString()}</td>
                  <td className="font-semibold text-slate-700">{(inst.teachers || 0).toLocaleString()}</td>
                  <td>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1.5 ${
                      inst.students > 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-slate-100 text-slate-500 border border-slate-200'
                    }`}>
                      {inst.students > 0 && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                      {inst.students > 0 ? 'Actif' : 'Vide'}
                    </span>
                  </td>
                  <td>
                    <button className="p-2 text-slate-400 hover:text-ucar-600 rounded-lg hover:bg-ucar-50 transition-colors">
                      <ExternalLink size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          )}
        </div>
      )}

      {/* Approvals Tab */}
      {activeTab === 'approvals' && (
        <div className="animate-fade">
          {pending.length === 0 ? (
            <div className="glass-card flex flex-col items-center justify-center py-16 text-center">
              <div className="w-20 h-20 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <CheckCircle size={40} />
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-2">Aucun dossier en attente</h3>
              <p className="text-slate-500 font-medium">Toutes les demandes d'inscription ont été traitées.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {pending.map(user => (
                <div key={user.id} className="glass-card flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 p-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-4 mb-3">
                      <div className="w-12 h-12 rounded-xl bg-accent-gradient flex items-center justify-center text-white font-bold text-xl shadow-md shrink-0">
                        {user.name?.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-bold text-lg text-slate-900 leading-tight">{user.name}</p>
                        <p className="text-sm font-medium text-slate-500 mt-1 flex items-center gap-2 flex-wrap">
                          <span>{user.email}</span>
                          <span className="w-1 h-1 rounded-full bg-slate-300" />
                          <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-600 font-semibold text-xs uppercase">{user.role}</span>
                          <span className="w-1 h-1 rounded-full bg-slate-300" />
                          <span className="text-ucar-600 font-semibold">{user.institution_id || 'UCAR HQ'}</span>
                        </p>
                      </div>
                    </div>
                    
                    {user.verification_result && (
                      <div className="ml-16 bg-slate-50 border border-slate-200 rounded-lg p-3 inline-flex flex-wrap items-center gap-4 text-xs font-medium text-slate-600">
                        <span className="flex items-center gap-1.5">
                          <Activity size={14} className="text-ucar-500" />
                          Score IA: <strong className={`text-sm ${user.verification_result.score >= 50 ? 'text-emerald-600' : 'text-amber-600'}`}>{user.verification_result.score}/100</strong>
                        </span>
                        {user.verification_result.ocr_name && (
                          <>
                            <span className="w-px h-4 bg-slate-300" />
                            <span>Nom OCR: <strong className="text-slate-800">{user.verification_result.ocr_name}</strong></span>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-3 w-full lg:w-auto ml-16 lg:ml-0">
                    <button 
                      onClick={() => handleApprove(user.id)} 
                      className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl font-bold transition-colors"
                    >
                      <CheckCircle size={18} /> Approuver
                    </button>
                    <button 
                      onClick={() => handleReject(user.id)} 
                      className="flex-1 lg:flex-none flex items-center justify-center gap-2 px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-xl font-bold transition-colors"
                    >
                      <XCircle size={18} /> Refuser
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
