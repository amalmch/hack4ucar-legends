import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import api from '../../api';
import { Camera, Save, User, Mail, Shield, Building } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  
  const [profile, setProfile] = useState({
    name: '',
    phone: '',
    bio: '',
    profile_image: ''
  });

  useEffect(() => {
    async function loadProfile() {
      try {
        const res = await api.get('/api/auth/me');
        setProfile({
          name: res.data.name || '',
          phone: res.data.phone || '',
          bio: res.data.bio || '',
          profile_image: res.data.profile_image || ''
        });
      } catch (err) {
        console.error("Erreur chargement profil", err);
      }
      setLoading(false);
    }
    loadProfile();
  }, []);

  const handleChange = (e) => {
    setProfile(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfile(prev => ({ ...prev, profile_image: reader.result }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put('/api/auth/profile', profile);
      setMsg('✅ Profil mis à jour avec succès');
    } catch (err) {
      setMsg('❌ Erreur lors de la mise à jour');
    }
    setSaving(false);
    setTimeout(() => setMsg(''), 3000);
  };

  if (loading) return (
    <div className="flex justify-center items-center h-64 text-slate-500 animate-pulse">
      Chargement du profil...
    </div>
  );

  return (
    <div className="animate-fade max-w-3xl mx-auto pb-10">
      <header className="mb-8">
        <h1 className="text-3xl font-display font-extrabold text-slate-900 mb-2 tracking-tight">Mon Profil</h1>
        <p className="text-slate-500 font-medium">Gérez vos informations personnelles et votre image de profil.</p>
      </header>

      {msg && (
        <div className={`mb-6 px-4 py-3 rounded-xl font-bold ${msg.includes('✅') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {msg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="glass-card flex flex-col gap-8">
        {/* En-tête du profil (Photo + Infos non modifiables) */}
        <div className="flex flex-col sm:flex-row gap-8 items-start sm:items-center">
          <div className="relative group shrink-0">
            <div className="w-28 h-28 rounded-2xl bg-slate-100 flex items-center justify-center border-2 border-slate-200 overflow-hidden shadow-inner">
              {profile.profile_image ? (
                <img src={profile.profile_image} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <User size={48} className="text-slate-300" />
              )}
            </div>
            <label className="absolute -bottom-3 -right-3 w-10 h-10 bg-ucar-600 text-white rounded-full flex items-center justify-center shadow-lg cursor-pointer hover:bg-ucar-700 transition-colors border-2 border-white">
              <Camera size={18} />
              <input type="file" accept="image/*" onChange={handleImageChange} className="hidden" />
            </label>
          </div>
          
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2 text-slate-600 text-sm">
              <Mail size={16} /> <strong>Email :</strong> {user?.email} <span className="text-xs text-slate-400 ml-2">(Non modifiable)</span>
            </div>
            <div className="flex items-center gap-2 text-slate-600 text-sm">
              <Shield size={16} /> <strong>Rôle :</strong> <span className="uppercase text-xs font-bold bg-slate-100 px-2 py-0.5 rounded text-slate-500">{user?.role}</span>
            </div>
            {user?.institution_id && (
              <div className="flex items-center gap-2 text-slate-600 text-sm">
                <Building size={16} /> <strong>Établissement :</strong> {user?.institution_id}
              </div>
            )}
          </div>
        </div>

        <hr className="border-slate-100" />

        {/* Champs modifiables */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-1 md:col-span-2">
            <label className="block text-sm font-bold text-slate-700">Nom et Prénom</label>
            <input 
              name="name"
              value={profile.name}
              onChange={handleChange}
              className="form-input w-full"
              placeholder="Votre nom complet"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="block text-sm font-bold text-slate-700">Téléphone</label>
            <input 
              name="phone"
              value={profile.phone}
              onChange={handleChange}
              className="form-input w-full"
              placeholder="Ex: +216 20 123 456"
            />
          </div>
          
          <div className="space-y-1 md:col-span-2">
            <label className="block text-sm font-bold text-slate-700">Biographie / À propos</label>
            <textarea 
              name="bio"
              value={profile.bio}
              onChange={handleChange}
              className="form-input w-full h-24 resize-none"
              placeholder="Décrivez votre rôle, vos intérêts académiques..."
            />
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-slate-100">
          <button 
            type="submit" 
            disabled={saving}
            className="flex items-center gap-2 px-6 py-3 bg-ucar-600 text-white rounded-xl font-bold hover:bg-ucar-700 shadow-md transition-all disabled:opacity-50"
          >
            {saving ? <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div> : <Save size={18} />}
            {saving ? 'Enregistrement...' : 'Enregistrer les modifications'}
          </button>
        </div>
      </form>
    </div>
  );
}
