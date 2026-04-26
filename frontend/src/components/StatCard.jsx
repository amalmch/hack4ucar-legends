import React from 'react';

export default function StatCard({ title, value, icon: Icon, trend, alert }) {
  return (
    <div className="glass-card group flex flex-col justify-between">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-sm font-semibold tracking-wider uppercase text-slate-500">
          {title}
        </h3>
        <div className={`p-3 rounded-xl transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3 ${
          alert ? 'bg-red-50 text-red-600' : 'bg-ucar-50 text-ucar-600'
        }`}>
          <Icon size={20} />
        </div>
      </div>
      
      <div className="flex items-end justify-between mt-2">
        <span className="font-display text-3xl font-extrabold tracking-tight text-slate-900">
          {value}
        </span>
        
        {trend && (
          <span className={`text-sm font-bold px-2 py-1 rounded-lg ${
            trend.startsWith('+') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
