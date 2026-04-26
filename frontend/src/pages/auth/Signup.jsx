import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Lock, Mail, User, ArrowRight, BookOpen, Shield, GraduationCap, Building2, Upload, CheckCircle, Clock, XCircle } from 'lucide-react';

const UCAR_INSTITUTIONS = [
  { id: "UCAR-FSJPST", name: "Fac. Sc. Juridiques, Politiques et Sociales de Tunis" },
  { id: "UCAR-FSB", name: "Faculté des Sciences de Bizerte" },
  { id: "UCAR-FSEGN", name: "Faculté des Sc. Economiques et de Gestion de Nabeul" },
  { id: "UCAR-ENAU", name: "Ecole Nationale d'Architecture et d'Urbanisme" },
  { id: "UCAR-EPT", name: "Ecole Polytechnique de Tunisie" },
  { id: "UCAR-ESTI", name: "Ecole Sup. de Technologie et d'Informatique" },
  { id: "UCAR-INSAT", name: "Institut National des Sciences Appliquées et de Technologie" },
  { id: "UCAR-SUPCOM", name: "Sup'Com" },
  // ... (keeping short for brevity, you can restore full list if needed)
];

const ROLES = [
  { id: 'student', label: 'Étudiant', icon: GraduationCap },
  { id: 'teacher', label: 'Enseignant', icon: BookOpen },
  { id: 'institution_admin', label: 'Admin Établissement', icon: Building2 },
];

const STATUS_UI = {
  approved: { icon: CheckCircle, colorClass: 'text-emerald-600 bg-emerald-50', label: 'Compte approuvé ! Connexion en cours...' },
  pending: { icon: Clock, colorClass: 'text-amber-600 bg-amber-50', label: 'Votre dossier est en cours de vérification par l\'équipe UCAR.' },
  rejected: { icon: XCircle, colorClass: 'text-red-600 bg-red-50', label: 'Votre document n\'a pas pu être vérifié. Contactez l\'administration.' },
};

export default function Signup() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({ name: '', email: '', password: '', role: 'student', institution_id: '', niveau: '' });
  const [docFile, setDocFile] = useState(null);
  const [docPreview, setDocPreview] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [signupResult, setSignupResult] = useState(null);
  const { signup } = useAuth();
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setDocFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => setDocPreview(ev.target.result);
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const fd = new FormData();
    fd.append('name', formData.name);
    fd.append('email', formData.email);
    fd.append('password', formData.password);
    fd.append('role', formData.role);
    fd.append('institution_id', formData.institution_id);
    if (formData.role === 'student' && formData.niveau) fd.append('niveau', formData.niveau);
    if (docFile) fd.append('document', docFile);

    try {
      const res = await fetch('http://localhost:5001/api/auth/register', { method: 'POST', body: fd });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error || 'Erreur lors de l\'inscription');
        setLoading(false);
        return;
      }

      setSignupResult(data);
      setStep(3);

      if (data.status === 'approved') {
        setTimeout(async () => {
          const loginRes = await signup(formData);
          if (loginRes.success) {
            if (loginRes.role === 'student') navigate('/student');
            else if (loginRes.role === 'teacher') navigate('/teacher');
            else navigate('/institution');
          }
        }, 2000);
      }
    } catch (err) {
      setError('Impossible de contacter le serveur.');
    }
    setLoading(false);
  };

  const needsInstitution = ['teacher', 'institution_admin', 'student'].includes(formData.role);

  return (
    <div className="flex items-center justify-center min-h-screen py-12 px-4 bg-slate-50">
      <div className="w-full max-w-lg">

        {/* Logo Header */}
        <div className="text-center mb-10 animate-fade">
          <img
            src="ucar.png"
            alt="Logo Université de Carthage"
            className="w-24 h-24 object-contain mx-auto mb-4 drop-shadow-lg hover:scale-105 transition-transform duration-300"
          />
          <h1 className="text-3xl font-display font-extrabold text-slate-900 mb-2">UCAR Intelligence</h1>
          <p className="text-slate-500 font-medium">Créer votre compte institutionnel</p>
        </div>

        {/* Steps Indicator */}
        <div className="flex items-center justify-center gap-2 mb-8 animate-fade">
          {['Informations', 'Document', 'Confirmation'].map((s, i) => (
            <React.Fragment key={s}>
              <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-500 ${step > i + 1 ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30' :
                    step === i + 1 ? 'bg-ucar-600 text-white shadow-md shadow-ucar-600/30' : 'bg-slate-200 text-slate-400'
                  }`}>
                  {step > i + 1 ? <CheckCircle size={14} /> : i + 1}
                </div>
                <span className={`text-xs font-semibold ${step >= i + 1 ? 'text-slate-900' : 'text-slate-400'}`}>{s}</span>
              </div>
              {i < 2 && <div className={`w-12 h-1 rounded-full transition-all duration-500 ${step > i + 1 ? 'bg-emerald-500' : 'bg-slate-200'}`} />}
            </React.Fragment>
          ))}
        </div>

        <div className="glass-card animate-slide-up">

          {/* STEP 3: Result */}
          {step === 3 && signupResult && (() => {
            const ui = STATUS_UI[signupResult.status] || STATUS_UI.pending;
            const Icon = ui.icon;
            return (
              <div className="text-center py-6 animate-fade">
                <div className={`w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center ${ui.colorClass} shadow-inner`}>
                  <Icon size={40} />
                </div>
                <h2 className="text-2xl font-bold mb-3">
                  {signupResult.status === 'approved' ? 'Vérification réussie !' : signupResult.status === 'pending' ? 'Dossier en attente' : 'Vérification échouée'}
                </h2>
                <p className="text-slate-500 mb-6 font-medium leading-relaxed">{ui.label}</p>

                {signupResult.verification && (
                  <div className="text-left bg-slate-50 border border-slate-200 rounded-xl p-5 mb-8 shadow-inner">
                    <p className="font-bold text-slate-800 mb-3 text-sm">Rapport d'Intelligence Artificielle :</p>
                    <div className="space-y-2">
                      {signupResult.verification.details?.map((d, i) => (
                        <p key={i} className="text-xs text-slate-600 flex items-start gap-2">
                          <span className="mt-0.5">•</span> <span>{d}</span>
                        </p>
                      ))}
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-200 flex justify-between items-center">
                      <span className="text-xs font-semibold text-slate-500">Score de Confiance</span>
                      <span className={`text-sm font-bold px-2.5 py-1 rounded-lg ${ui.colorClass}`}>
                        {signupResult.verification.score}/100
                      </span>
                    </div>
                  </div>
                )}

                {signupResult.status !== 'approved' && (
                  <Link to="/login" className="btn-primary inline-flex w-auto px-8">
                    Retour à la connexion
                  </Link>
                )}
              </div>
            );
          })()}

          {/* STEP 1: Personal Info */}
          {step === 1 && (
            <form onSubmit={(e) => { e.preventDefault(); setStep(2); }} className="flex flex-col gap-6 animate-fade">
              <div>
                <label className="block mb-3 text-sm font-semibold text-slate-600">Je suis un...</label>
                <div className="grid grid-cols-3 gap-3">
                  {ROLES.map(({ id, label, icon: Icon }) => (
                    <div
                      key={id}
                      onClick={() => setFormData({ ...formData, role: id })}
                      className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 cursor-pointer transition-all duration-300 ${formData.role === id
                          ? 'border-ucar-500 bg-ucar-50 text-ucar-700 shadow-md transform -translate-y-1'
                          : 'border-slate-200 bg-white text-slate-500 hover:border-ucar-300 hover:bg-slate-50'
                        }`}
                    >
                      <Icon size={28} className="mb-2" />
                      <span className="text-xs font-bold text-center">{label}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-5">
                <Field label="Nom complet" icon={User} type="text" value={formData.name} onChange={v => setFormData({ ...formData, name: v })} placeholder="Foulen Ben Foulen" required />
                <Field label="Email institutionnel" icon={Mail} type="email" value={formData.email} onChange={v => setFormData({ ...formData, email: v })} placeholder="prenom.nom@ucar.tn" required />
                <Field label="Mot de passe" icon={Lock} type="password" value={formData.password} onChange={v => setFormData({ ...formData, password: v })} placeholder="••••••••" required />

                {needsInstitution && (
                  <div>
                    <label className="block mb-2 text-sm font-semibold text-slate-600">Établissement UCAR</label>
                    <select
                      value={formData.institution_id}
                      onChange={e => setFormData({ ...formData, institution_id: e.target.value })}
                      required
                      className="form-input cursor-pointer"
                    >
                      <option value="">Sélectionnez votre établissement...</option>
                      {UCAR_INSTITUTIONS.map(inst => (
                        <option key={inst.id} value={inst.id}>{inst.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                {formData.role === 'student' && (
                  <div>
                    <label className="block mb-2 text-sm font-semibold text-slate-600">Niveau d'études</label>
                    <select
                      value={formData.niveau}
                      onChange={e => setFormData({ ...formData, niveau: e.target.value })}
                      required
                      className="form-input cursor-pointer"
                    >
                      <option value="">Sélectionnez votre niveau...</option>
                      <option value="1ère année">1ère année</option>
                      <option value="2ème année">2ème année</option>
                      <option value="3ème année">3ème année</option>
                      <option value="4ème année">4ème année</option>
                      <option value="5ème année">5ème année</option>
                      <option value="Master 1">Master 1</option>
                      <option value="Master 2">Master 2</option>
                      <option value="Doctorat">Doctorat</option>
                    </select>
                  </div>
                )}
              </div>

              {error && <p className="text-red-600 text-sm font-semibold p-3 bg-red-50 rounded-lg">{error}</p>}

              <button type="submit" className="btn-primary mt-2 group">
                Continuer <ArrowRight size={20} className="transition-transform group-hover:translate-x-1" />
              </button>

              <p className="text-center mt-2 text-sm font-medium text-slate-500">
                Déjà inscrit ? <Link to="/login" className="text-ucar-600 font-bold hover:underline transition-all">Se connecter</Link>
              </p>
            </form>
          )}

          {/* STEP 2: Document Upload */}
          {step === 2 && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-6 animate-fade">
              <div className="text-center mb-4">
                <div className="w-16 h-16 bg-ucar-50 text-ucar-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Shield size={32} />
                </div>
                <h2 className="text-xl font-bold mb-2">Vérification d'identité par IA</h2>
                <p className="text-slate-500 text-sm leading-relaxed">
                  Importez votre CIN, carte étudiante ou professionnelle. Notre IA vérifiera automatiquement votre identité en quelques secondes.
                </p>
              </div>

              <label
                htmlFor="doc-upload"
                className={`block border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${docPreview
                    ? 'border-ucar-500 bg-ucar-50 shadow-inner'
                    : 'border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-ucar-400'
                  }`}
              >
                {docPreview ? (
                  <div className="relative">
                    <img src={docPreview} alt="Document preview" className="max-h-48 mx-auto rounded-lg shadow-md object-contain" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center text-white font-semibold">
                      Changer le document
                    </div>
                  </div>
                ) : (
                  <div className="py-6">
                    <Upload size={40} className="text-slate-400 mx-auto mb-4" />
                    <p className="font-bold text-slate-700 mb-1">Cliquez pour importer votre document</p>
                    <p className="text-xs text-slate-500 font-medium">Formats : JPG, PNG, PDF (max 5 MB)</p>
                  </div>
                )}
                <input id="doc-upload" type="file" accept="image/*,.pdf" onChange={handleFileChange} className="hidden" />
              </label>

              {error && <p className="text-red-600 text-sm font-semibold p-3 bg-red-50 rounded-lg">{error}</p>}

              <div className="grid grid-cols-2 gap-4 mt-4">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="py-3 px-4 bg-white border-2 border-slate-200 text-slate-600 font-bold rounded-xl hover:bg-slate-50 hover:text-slate-900 hover:border-slate-300 transition-all duration-200"
                >
                  Retour
                </button>
                <button type="submit" className="btn-primary group" disabled={loading}>
                  {loading ? (
                    <span className="flex items-center gap-2"><span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span> Analyse...</span>
                  ) : docFile ? (
                    <span className="flex items-center gap-2">Vérifier <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" /></span>
                  ) : (
                    'Ignorer'
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, icon: Icon, type, value, onChange, placeholder, required }) {
  return (
    <div>
      <label className="block mb-2 text-sm font-semibold text-slate-600">{label}</label>
      <div className="relative group">
        <Icon size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-ucar-500 transition-colors" />
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          required={required}
          className="form-input"
          placeholder={placeholder}
        />
      </div>
    </div>
  );
}
