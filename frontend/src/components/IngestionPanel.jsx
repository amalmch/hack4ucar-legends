import React, { useState, useCallback } from 'react';
import api from '../api';
import { Upload, FileText, CheckCircle, AlertTriangle, Loader, X, FileSpreadsheet, Image } from 'lucide-react';

const FILE_ICONS = {
  pdf: FileText,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  csv: FileSpreadsheet,
  png: Image,
  jpg: Image,
  jpeg: Image,
};

export default function IngestionPanel({ institutionId }) {
  const [file, setFile] = useState(null);
  const [periode, setPeriode] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      setFile(dropped);
      setResult(null);
      setError('');
    }
  }, []);

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setResult(null);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('periode', periode);
      if (institutionId) {
        formData.append('institution_id', institutionId);
      }

      const res = await api.post('/api/ingestion/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
      setFile(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Erreur lors de l\'upload');
    }
    setUploading(false);
  };

  const ext = file?.name?.split('.').pop()?.toLowerCase();
  const IconComp = ext ? (FILE_ICONS[ext] || FileText) : FileText;

  return (
    <div className="glass-card mb-8 animate-fade">
      <h3 className="text-lg font-display font-extrabold text-slate-800 mb-1 flex items-center gap-2">
        <Upload className="text-ucar-600" size={22} />
        Pipeline d'Ingestion de Données
      </h3>
      <p className="text-sm text-slate-500 mb-5">
        Uploadez un fichier (PDF, Excel, CSV, Image) pour extraire et charger automatiquement les KPIs.
      </p>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 cursor-pointer ${
          dragOver
            ? 'border-ucar-500 bg-ucar-50 scale-[1.02]'
            : file
              ? 'border-emerald-300 bg-emerald-50/50'
              : 'border-slate-200 bg-slate-50/50 hover:border-ucar-300 hover:bg-ucar-50/30'
        }`}
        onClick={() => !file && document.getElementById('ingestion-file-input').click()}
      >
        <input
          id="ingestion-file-input"
          type="file"
          accept=".pdf,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.tiff"
          onChange={handleFileSelect}
          className="hidden"
        />

        {file ? (
          <div className="flex items-center justify-center gap-4">
            <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center">
              <IconComp size={28} className="text-emerald-600" />
            </div>
            <div className="text-left">
              <p className="font-bold text-slate-800">{file.name}</p>
              <p className="text-xs text-slate-500">
                {(file.size / 1024).toFixed(1)} KB — Prêt pour l'ingestion
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null); }}
              className="ml-4 p-2 rounded-full hover:bg-red-100 text-slate-400 hover:text-red-600 transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        ) : (
          <div>
            <Upload size={40} className="mx-auto text-slate-300 mb-3" />
            <p className="font-bold text-slate-600">Glissez-déposez un fichier ici</p>
            <p className="text-xs text-slate-400 mt-1">
              ou cliquez pour parcourir — PDF, Excel, CSV, Image
            </p>
          </div>
        )}
      </div>

      {/* Period input + upload button */}
      {file && (
        <div className="flex flex-col sm:flex-row gap-3 mt-4 animate-fade">
          <input
            type="text"
            value={periode}
            onChange={(e) => setPeriode(e.target.value)}
            placeholder="Période (ex: 2024, 2024-01)"
            className="flex-1 bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-ucar-500/20 focus:border-ucar-400 transition-all"
          />
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="flex items-center justify-center gap-2 px-6 py-2.5 bg-ucar-600 text-white rounded-xl font-bold text-sm hover:bg-ucar-700 disabled:opacity-50 transition-all shadow-lg shadow-ucar-600/20"
          >
            {uploading ? (
              <>
                <Loader size={16} className="animate-spin" />
                Traitement...
              </>
            ) : (
              <>
                <Upload size={16} />
                Lancer l'ingestion
              </>
            )}
          </button>
        </div>
      )}

      {result && (() => {
        const typeLabels = {
          students:       { emoji: '🎒', label: 'Étudiants',      color: 'emerald' },
          teachers:       { emoji: '👨‍🏫', label: 'Enseignants',    color: 'indigo'  },
          institutions:   { emoji: '🏛️', label: 'Établissements', color: 'violet'  },
          kpi_ingested:   { emoji: '📊', label: 'KPIs',            color: 'blue'    },
          unknown:        { emoji: '📁', label: 'Données',         color: 'slate'   },
        };
        const dt = typeLabels[result.data_type] || typeLabels.unknown;
        return (
          <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3 animate-fade">
            <CheckCircle className="text-emerald-600 mt-0.5 shrink-0" size={20} />
            <div>
              <p className="font-bold text-emerald-800">{result.message}</p>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-full bg-${dt.color}-100 text-${dt.color}-800 border border-${dt.color}-200`}>
                  {dt.emoji} Détecté : {dt.label}
                </span>
                <span className="text-xs text-emerald-600">
                  Fichier : {result.fichier}
                </span>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 animate-fade">
          <AlertTriangle className="text-red-600 mt-0.5 shrink-0" size={20} />
          <div>
            <p className="font-bold text-red-800">Erreur</p>
            <p className="text-xs text-red-600 mt-1">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
