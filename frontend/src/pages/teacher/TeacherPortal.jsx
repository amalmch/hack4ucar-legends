import React, { useState, useEffect } from 'react';
import api from '../../api';
import StatCard from '../../components/StatCard';
import { Users, BookOpen, FileText, Calendar, Plus, Trash2, Clock, Award, Search, ChevronDown, ChevronUp } from 'lucide-react';

export default function TeacherPortal() {
  const [stats, setStats] = useState({classes:0,students:0,courses:0,upcoming_exams:0});
  const [classes, setClasses] = useState([]);
  const [courses, setCourses] = useState([]);
  const [exams, setExams] = useState([]);
  const [grades, setGrades] = useState([]);
  const [profile, setProfile] = useState({});
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [expandedClass, setExpandedClass] = useState(null);
  const [showAddCourse, setShowAddCourse] = useState(false);
  const [showAddExam, setShowAddExam] = useState(false);
  const [newCourse, setNewCourse] = useState({subject:'',niveau:'',title:'',description:''});
  const [newExam, setNewExam] = useState({subject:'',niveau:'',type:'DS',date:'',salle:'',duree_minutes:60});
  const [selectedNiveau, setSelectedNiveau] = useState('');
  const [msg, setMsg] = useState('');

  // Grade editing state
  const [editingMode, setEditingMode] = useState(false);
  const [editingClassIndex, setEditingClassIndex] = useState('');
  const [editingSubject, setEditingSubject] = useState('');
  const [draftGrades, setDraftGrades] = useState({});

  useEffect(() => {
    async function load() {
      try {
        const [s, c, co, e, g, p] = await Promise.all([
          api.get('/api/teacher/stats'),
          api.get('/api/teacher/classes'),
          api.get('/api/teacher/courses'),
          api.get('/api/teacher/exams'),
          api.get('/api/teacher/grades'),
          api.get('/api/teacher/profile'),
        ]);
        setStats(s.data);
        setClasses(c.data.classes || []);
        setCourses(co.data.courses || []);
        setExams(e.data.exams || []);
        setGrades(g.data.grades || []);
        setProfile(p.data || {});
      } catch(e) { console.error(e); }
      setLoading(false);
    }
    load();
  }, []);

  const flash = (m) => { setMsg(m); setTimeout(() => setMsg(''), 3000); };

  const handleAddCourse = async () => {
    try {
      await api.post('/api/teacher/courses', newCourse);
      const res = await api.get('/api/teacher/courses');
      setCourses(res.data.courses || []);
      setShowAddCourse(false);
      setNewCourse({subject:'',niveau:'',title:'',description:''});
      flash('✅ Cours ajouté');
    } catch(e) { flash('❌ Erreur'); }
  };

  const handleDeleteCourse = async (id) => {
    await api.delete(`/api/teacher/courses/${id}`);
    setCourses(courses.filter(c => c.id !== id));
    flash('🗑️ Cours supprimé');
  };

  const handleAddExam = async () => {
    try {
      await api.post('/api/teacher/exams', newExam);
      const res = await api.get('/api/teacher/exams');
      setExams(res.data.exams || []);
      setShowAddExam(false);
      setNewExam({subject:'',niveau:'',type:'DS',date:'',salle:'',duree_minutes:60});
      flash('✅ Examen programmé');
    } catch(e) { flash('❌ Erreur'); }
  };

  const handleStartEditingGrades = () => {
    if (editingClassIndex === '' || !editingSubject) {
      flash('⚠️ Veuillez sélectionner une classe et une matière.');
      return;
    }
    const cls = classes[editingClassIndex];
    const initialDrafts = {};
    cls.students.forEach(s => {
      // Find existing grade for this student and subject
      const existing = grades.find(g => g.student_id === s.student_id && g.subject === editingSubject);
      initialDrafts[s.student_id] = {
        ds: existing ? existing.ds : 0,
        examen: existing ? existing.examen : 0,
        tp: existing ? existing.tp : 0,
        absences: existing ? existing.absences : 0,
      };
    });
    setDraftGrades(initialDrafts);
    setEditingMode(true);
  };

  const handleDraftChange = (studentId, field, value) => {
    setDraftGrades(prev => ({
      ...prev,
      [studentId]: { ...prev[studentId], [field]: parseFloat(value) || 0 }
    }));
  };

  const handleSaveGrades = async () => {
    const cls = classes[editingClassIndex];
    const payload = Object.keys(draftGrades).map(studentId => ({
      student_id: studentId,
      subject: editingSubject,
      niveau: cls.niveau,
      ds: draftGrades[studentId].ds,
      examen: draftGrades[studentId].examen,
      tp: draftGrades[studentId].tp,
      absences: draftGrades[studentId].absences,
    }));

    try {
      await api.post('/api/teacher/grades', { grades: payload });
      const res = await api.get('/api/teacher/grades');
      setGrades(res.data.grades || []);
      setEditingMode(false);
      flash('✅ Notes publiées avec succès ! Les étudiants ont été notifiés.');
    } catch(e) {
      flash('❌ Erreur lors de la publication des notes.');
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin" />
        <p className="font-medium">Chargement du portail enseignant...</p>
      </div>
    </div>
  );

  const tabs = ['overview','classes','courses','exams','grades'];
  const tabLabels = {'overview':'Vue Globale','classes':`Classes (${classes.length})`,'courses':`Supports (${courses.length})`,'exams':`Examens (${exams.length})`,'grades':'Notes'};

  const niveaux = [...new Set(classes.map(c => c.niveau))];
  const filteredGrades = selectedNiveau ? grades.filter(g => g.niveau === selectedNiveau) : grades;

  return (
    <div className="animate-fade max-w-7xl mx-auto pb-10">
      <header className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold uppercase tracking-wider border border-emerald-100 shadow-sm">Espace Enseignant</span>
          {profile.classes_enseignees && profile.classes_enseignees.length > 0 && (
            <span className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-bold border border-indigo-100">
              Classes enseignées : {profile.classes_enseignees.join(", ")}
            </span>
          )}
        </div>
        <h1 className="text-3xl sm:text-4xl font-display font-extrabold text-slate-900 mb-1 tracking-tight">
          {profile.prenom ? `Bienvenue, Prof. ${profile.prenom} ${profile.nom}` : 'Portail Enseignant'}
        </h1>
        <p className="text-slate-500 font-medium text-sm">Gérez vos classes, cours, examens et notes.</p>
      </header>

      {msg && <div className="mb-4 px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm font-bold text-sm animate-fade">{msg}</div>}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard title="Classes" value={stats.classes} icon={Users} />
        <StatCard title="Étudiants" value={stats.students} icon={Users} />
        <StatCard title="Supports de cours" value={stats.courses} icon={FileText} />
        <StatCard title="Examens à venir" value={stats.upcoming_exams} icon={Calendar} />
      </div>

      <div className="flex gap-2 sm:gap-6 mb-8 border-b border-slate-200 overflow-x-auto no-scrollbar">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`whitespace-nowrap px-4 py-4 border-b-2 font-bold text-sm transition-all duration-300 ${activeTab === t ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'}`}>
            {tabLabels[t]}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade">
          <div className="glass-card">
            <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-3"><div className="w-2 h-6 bg-emerald-500 rounded-full"/>Examens à venir</h3>
            {exams.filter(e => e.status === 'upcoming').slice(0,5).map((e,i) => (
              <div key={i} className="flex justify-between items-center py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50 px-2 rounded-lg transition-colors">
                <div>
                  <p className="font-bold text-sm text-slate-800">{e.subject}</p>
                  <p className="text-xs text-slate-500">{e.type} — {e.niveau} — {e.salle}</p>
                </div>
                <span className="text-xs font-bold px-2 py-1 bg-rose-50 text-rose-700 rounded border border-rose-100">{new Date(e.date).toLocaleDateString('fr-FR')}</span>
              </div>
            ))}
            {exams.filter(e => e.status === 'upcoming').length === 0 && <p className="text-sm text-slate-500 py-4 text-center">Aucun examen à venir</p>}
          </div>
          <div className="glass-card">
            <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-3"><div className="w-2 h-6 bg-blue-500 rounded-full"/>Derniers cours ajoutés</h3>
            {courses.slice(0,5).map((c,i) => (
              <div key={i} className="flex justify-between items-center py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50 px-2 rounded-lg transition-colors">
                <div>
                  <p className="font-bold text-sm text-slate-800">{c.title}</p>
                  <p className="text-xs text-slate-500">{c.subject} — {c.niveau}</p>
                </div>
                <span className="text-xs font-bold px-2 py-1 bg-blue-50 text-blue-700 rounded border border-blue-100">{c.file_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Classes */}
      {activeTab === 'classes' && (
        <div className="space-y-4 animate-fade">
          {classes.map((cls, i) => (
            <div key={i} className="glass-card">
              <button onClick={() => setExpandedClass(expandedClass === i ? null : i)} className="w-full flex justify-between items-center">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg">{cls.niveau}</div>
                  <div className="text-left">
                    <p className="font-bold text-slate-800">{cls.programme} — {cls.niveau}</p>
                    <p className="text-xs text-slate-500">{cls.count} étudiants</p>
                  </div>
                </div>
                {expandedClass === i ? <ChevronUp size={20} className="text-slate-400"/> : <ChevronDown size={20} className="text-slate-400"/>}
              </button>
              {expandedClass === i && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <div className="table-container">
                    <table>
                      <thead><tr><th>Étudiant</th><th>Genre</th><th>Moy. S1</th><th>Absences</th><th>Statut</th></tr></thead>
                      <tbody>
                        {cls.students.slice(0,50).map((s,j) => (
                          <tr key={j}>
                            <td className="font-bold text-slate-800">{s.prenom} {s.nom}</td>
                            <td className="text-slate-500">{s.genre}</td>
                            <td className={`font-bold ${parseFloat(s.moyenne_s1) < 10 ? 'text-red-600' : 'text-slate-700'}`}>{s.moyenne_s1}</td>
                            <td className={`font-semibold ${parseInt(s.nb_absences_s1) > 3 ? 'text-red-600' : 'text-slate-600'}`}>{s.nb_absences_s1}</td>
                            <td><span className={`px-2 py-1 rounded text-xs font-bold ${s.statut === 'abandonne' ? 'bg-red-50 text-red-700' : s.statut === 'diplome' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{s.statut}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Courses */}
      {activeTab === 'courses' && (
        <div className="animate-fade">
          <button onClick={() => setShowAddCourse(!showAddCourse)} className="mb-6 flex items-center gap-2 px-5 py-3 bg-emerald-600 text-white rounded-xl font-bold text-sm hover:bg-emerald-700 transition-all shadow-lg shadow-emerald-600/20">
            <Plus size={18}/> Ajouter un cours
          </button>
          {showAddCourse && (
            <div className="glass-card mb-6 animate-fade">
              <h3 className="font-bold text-slate-800 mb-4">Nouveau support de cours</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input value={newCourse.subject} onChange={e => setNewCourse({...newCourse, subject: e.target.value})} placeholder="Matière" className="form-input"/>
                <input value={newCourse.niveau} onChange={e => setNewCourse({...newCourse, niveau: e.target.value})} placeholder="Niveau (L1, M1...)" className="form-input"/>
                <input value={newCourse.title} onChange={e => setNewCourse({...newCourse, title: e.target.value})} placeholder="Titre du document" className="form-input sm:col-span-2"/>
                <input value={newCourse.description} onChange={e => setNewCourse({...newCourse, description: e.target.value})} placeholder="Description" className="form-input sm:col-span-2"/>
              </div>
              <button onClick={handleAddCourse} className="mt-4 px-5 py-2 bg-emerald-600 text-white rounded-xl font-bold text-sm hover:bg-emerald-700 transition-all">Enregistrer</button>
            </div>
          )}
          <div className="table-container">
            <table>
              <thead><tr><th>Titre</th><th>Matière</th><th>Niveau</th><th>Type</th><th>Actions</th></tr></thead>
              <tbody>
                {courses.map((c,i) => (
                  <tr key={i}>
                    <td className="font-bold text-slate-800">{c.title}</td>
                    <td className="text-slate-600">{c.subject}</td>
                    <td><span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-bold border border-blue-100">{c.niveau}</span></td>
                    <td className="text-slate-500 uppercase text-xs font-bold">{c.file_type}</td>
                    <td><button onClick={() => handleDeleteCourse(c.id)} className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"><Trash2 size={16}/></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Exams */}
      {activeTab === 'exams' && (
        <div className="animate-fade">
          <button onClick={() => setShowAddExam(!showAddExam)} className="mb-6 flex items-center gap-2 px-5 py-3 bg-rose-600 text-white rounded-xl font-bold text-sm hover:bg-rose-700 transition-all shadow-lg shadow-rose-600/20">
            <Plus size={18}/> Programmer un examen
          </button>
          {showAddExam && (
            <div className="glass-card mb-6 animate-fade">
              <h3 className="font-bold text-slate-800 mb-4">Nouvel examen</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <input value={newExam.subject} onChange={e => setNewExam({...newExam, subject: e.target.value})} placeholder="Matière" className="form-input"/>
                <input value={newExam.niveau} onChange={e => setNewExam({...newExam, niveau: e.target.value})} placeholder="Niveau" className="form-input"/>
                <select value={newExam.type} onChange={e => setNewExam({...newExam, type: e.target.value})} className="form-input">
                  <option value="DS">DS</option><option value="Examen">Examen</option><option value="TP">TP</option>
                </select>
                <input type="datetime-local" value={newExam.date} onChange={e => setNewExam({...newExam, date: e.target.value})} className="form-input"/>
                <input value={newExam.salle} onChange={e => setNewExam({...newExam, salle: e.target.value})} placeholder="Salle" className="form-input"/>
                <input type="number" value={newExam.duree_minutes} onChange={e => setNewExam({...newExam, duree_minutes: parseInt(e.target.value)})} placeholder="Durée (min)" className="form-input"/>
              </div>
              <button onClick={handleAddExam} className="mt-4 px-5 py-2 bg-rose-600 text-white rounded-xl font-bold text-sm hover:bg-rose-700 transition-all">Programmer</button>
            </div>
          )}
          <div className="table-container">
            <table>
              <thead><tr><th>Matière</th><th>Type</th><th>Niveau</th><th>Date</th><th>Salle</th><th>Durée</th><th>Statut</th></tr></thead>
              <tbody>
                {exams.map((e,i) => (
                  <tr key={i}>
                    <td className="font-bold text-slate-800">{e.subject}</td>
                    <td><span className={`px-2 py-1 rounded text-xs font-bold ${e.type === 'Examen' ? 'bg-rose-50 text-rose-700 border border-rose-100' : 'bg-amber-50 text-amber-700 border border-amber-100'}`}>{e.type}</span></td>
                    <td className="text-slate-600 font-medium">{e.niveau}</td>
                    <td className="text-sm font-medium text-slate-700">{new Date(e.date).toLocaleDateString('fr-FR')} {new Date(e.date).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})}</td>
                    <td className="text-slate-600">{e.salle}</td>
                    <td className="text-slate-500">{e.duree_minutes}min</td>
                    <td><span className={`px-2 py-1 rounded text-xs font-bold ${e.status === 'upcoming' ? 'bg-blue-50 text-blue-700 border border-blue-100' : 'bg-slate-100 text-slate-500'}`}>{e.status === 'upcoming' ? 'À venir' : 'Passé'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Grades */}
      {activeTab === 'grades' && (
        <div className="animate-fade">
          {!editingMode ? (
            <>
              <div className="glass-card mb-6">
                <h3 className="font-bold text-slate-800 mb-4">Saisir ou modifier des notes</h3>
                <div className="flex flex-col sm:flex-row gap-3 items-end">
                  <div className="flex-1">
                    <label className="block text-xs font-bold text-slate-500 mb-1">Classe</label>
                    <select value={editingClassIndex} onChange={e => setEditingClassIndex(e.target.value)} className="form-input w-full">
                      <option value="">-- Sélectionner une classe --</option>
                      {classes.map((cls, i) => <option key={i} value={i}>{cls.programme} — {cls.niveau}</option>)}
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="block text-xs font-bold text-slate-500 mb-1">Matière</label>
                    <input value={editingSubject} onChange={e => setEditingSubject(e.target.value)} placeholder="Ex: Mathématiques, Algorithmique..." className="form-input w-full"/>
                  </div>
                  <button onClick={handleStartEditingGrades} className="px-6 py-2.5 bg-emerald-600 text-white rounded-xl font-bold text-sm hover:bg-emerald-700 transition-all shrink-0 h-[42px]">
                    Saisir les notes
                  </button>
                </div>
              </div>

              <div className="flex gap-3 mb-6 flex-wrap">
                <button onClick={() => setSelectedNiveau('')} className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${!selectedNiveau ? 'bg-emerald-600 text-white shadow-lg' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'}`}>Tous</button>
                {niveaux.map(n => (
                  <button key={n} onClick={() => setSelectedNiveau(n)} className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${selectedNiveau === n ? 'bg-emerald-600 text-white shadow-lg' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'}`}>{n}</button>
                ))}
              </div>
              <div className="table-container">
                <table>
                  <thead><tr><th>Étudiant</th><th>Matière</th><th>DS</th><th>Examen</th><th>TP</th><th>Moyenne</th><th>Abs.</th><th>Statut</th></tr></thead>
                  <tbody>
                    {filteredGrades.slice(0,100).map((g,i) => (
                      <tr key={i}>
                        <td className="font-bold text-slate-800 text-xs">{g.student_id}</td>
                        <td className="text-sm text-slate-600 font-medium">{g.subject}</td>
                        <td className="font-semibold text-slate-700">{g.ds}</td>
                        <td className="font-semibold text-slate-700">{g.examen}</td>
                        <td className="font-semibold text-slate-700">{g.tp}</td>
                        <td className={`font-bold ${g.moyenne < 10 ? 'text-red-600' : 'text-emerald-600'}`}>{g.moyenne}</td>
                        <td className={`font-semibold ${g.absences > 3 ? 'text-red-600' : 'text-slate-600'}`}>{g.absences}</td>
                        <td>{g.eliminated ? <span className="px-2 py-1 bg-red-50 text-red-700 rounded text-xs font-bold border border-red-100">Éliminé</span> : <span className="px-2 py-1 bg-emerald-50 text-emerald-700 rounded text-xs font-bold border border-emerald-100">Admis</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="glass-card animate-fade">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="font-bold text-slate-800 text-xl">Saisie des notes : {editingSubject}</h3>
                  <p className="text-sm text-slate-500 mt-1">Classe : {classes[editingClassIndex]?.programme} — {classes[editingClassIndex]?.niveau}</p>
                </div>
                <div className="flex gap-3">
                  <button onClick={() => setEditingMode(false)} className="px-4 py-2 border border-slate-200 text-slate-600 font-bold rounded-xl hover:bg-slate-50">Annuler</button>
                  <button onClick={handleSaveGrades} className="px-6 py-2 bg-emerald-600 text-white font-bold rounded-xl shadow-lg hover:bg-emerald-700">Publier les notes</button>
                </div>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Étudiant</th>
                      <th>DS (30%)</th>
                      <th>Examen (50%)</th>
                      <th>TP (20%)</th>
                      <th>Absences (Max 3)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {classes[editingClassIndex]?.students.map((s, i) => (
                      <tr key={i}>
                        <td>
                          <p className="font-bold text-slate-800">{s.prenom} {s.nom}</p>
                          <p className="text-xs text-slate-500 font-mono">{s.student_id}</p>
                        </td>
                        <td><input type="number" step="0.25" min="0" max="20" value={draftGrades[s.student_id]?.ds || ''} onChange={e => handleDraftChange(s.student_id, 'ds', e.target.value)} className="form-input w-24 text-center p-1.5"/></td>
                        <td><input type="number" step="0.25" min="0" max="20" value={draftGrades[s.student_id]?.examen || ''} onChange={e => handleDraftChange(s.student_id, 'examen', e.target.value)} className="form-input w-24 text-center p-1.5"/></td>
                        <td><input type="number" step="0.25" min="0" max="20" value={draftGrades[s.student_id]?.tp || ''} onChange={e => handleDraftChange(s.student_id, 'tp', e.target.value)} className="form-input w-24 text-center p-1.5"/></td>
                        <td><input type="number" min="0" max="100" value={draftGrades[s.student_id]?.absences || ''} onChange={e => handleDraftChange(s.student_id, 'absences', e.target.value)} className="form-input w-24 text-center p-1.5"/></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
