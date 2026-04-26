import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Lock, Mail, ArrowRight } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const res = await login(email, password);
    if (res.success) {
      if (res.role === 'student') navigate('/student');
      else if (res.role === 'teacher') navigate('/teacher');
      else if (res.role === 'institution_admin') navigate('/institution');
      else navigate('/ucar');
    } else {
      setError(res.message);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen w-full bg-slate-50 p-6">
      <div className="w-full max-w-md animate-fade">
        <div className="glass-card">
          <div className="text-center mb-10">
            <img
              src="/ucar.png"
              alt="Logo Université de Carthage"
              className="w-24 h-24 object-contain mx-auto mb-4 drop-shadow-lg hover:scale-105 transition-transform duration-300"
            />
            <h1 className="text-3xl font-display font-extrabold text-slate-900 mb-2">Bienvenue sur UCAR</h1>
            <p className="text-slate-500 font-medium">Connectez-vous à votre portail</p>
          </div>

          {error && (
            <div className="alert-banner alert-critical mb-6 py-3 px-4">
              <span className="text-sm font-semibold">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <div>
              <label className="block mb-2 text-sm font-semibold text-slate-600">Email institutionnel</label>
              <div className="relative group">
                <Mail size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-ucar-500 transition-colors" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="form-input"
                  placeholder="prenom.nom@ucar.tn"
                />
              </div>
            </div>

            <div>
              <label className="block mb-2 text-sm font-semibold text-slate-600">Mot de passe</label>
              <div className="relative group">
                <Lock size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-ucar-500 transition-colors" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="form-input"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button type="submit" className="btn-primary mt-4 group">
              Se connecter
              <ArrowRight size={20} className="transition-transform duration-300 group-hover:translate-x-1" />
            </button>
          </form>

          <p className="text-center mt-8 text-sm font-medium text-slate-500">
            Pas encore de compte ?{' '}
            <Link to="/signup" className="text-ucar-600 hover:text-ucar-800 font-bold hover:underline transition-colors">
              Créer un compte
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
