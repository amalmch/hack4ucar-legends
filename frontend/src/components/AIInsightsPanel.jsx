import React, { useState, useEffect } from 'react';
import api from '../api';
import { AlertTriangle, TrendingUp, Info, ShieldAlert, Sparkles } from 'lucide-react';

export default function AIInsightsPanel({ institutionId }) {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchInsights() {
      try {
        const url = institutionId ? `/api/ai/insights?institution_id=${institutionId}` : '/api/ai/insights';
        const res = await api.get(url);
        setInsights(res.data.insights || []);
      } catch (err) {
        console.error("Failed to fetch AI Insights", err);
      }
      setLoading(false);
    }
    fetchInsights();
  }, []);

  if (loading) return null;
  if (insights.length === 0) return null;

  return (
    <div className="glass-card mb-8 animate-fade border-l-4 border-ucar-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-display font-extrabold text-slate-800 flex items-center gap-2">
          <Sparkles className="text-ucar-500" size={22} />
          UCAR Intelligence - Détection & Prédictions
        </h3>
        <span className="text-xs font-bold px-2 py-1 bg-ucar-50 text-ucar-700 rounded border border-ucar-100">
          Mise à jour en temps réel
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {insights.map((insight) => {
          let Icon = Info;
          let colorClass = "bg-slate-50 text-slate-700 border-slate-200";
          let iconColorClass = "text-slate-500 bg-slate-100";

          if (insight.severity === 'critical') {
            Icon = ShieldAlert;
            colorClass = "bg-red-50 text-red-900 border-red-200";
            iconColorClass = "text-red-600 bg-red-100";
          } else if (insight.severity === 'warning') {
            Icon = AlertTriangle;
            colorClass = "bg-amber-50 text-amber-900 border-amber-200";
            iconColorClass = "text-amber-600 bg-amber-100";
          } else if (insight.severity === 'success') {
            Icon = TrendingUp;
            colorClass = "bg-emerald-50 text-emerald-900 border-emerald-200";
            iconColorClass = "text-emerald-600 bg-emerald-100";
          }

          return (
            <div key={insight.id} className={`p-4 rounded-xl border ${colorClass} flex gap-4 transition-transform hover:-translate-y-1 duration-300`}>
              <div className={`p-3 rounded-xl h-fit ${iconColorClass}`}>
                <Icon size={24} />
              </div>
              <div>
                <h4 className="font-bold text-sm mb-1">{insight.title}</h4>
                <p className="text-xs opacity-90 mb-2 leading-relaxed">{insight.description}</p>
                <div className="text-xs font-semibold bg-white/50 inline-block px-2 py-1 rounded">
                  Action : {insight.action_recommended}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
