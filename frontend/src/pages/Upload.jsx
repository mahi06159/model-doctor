import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileCode, FileSpreadsheet, ShieldAlert, 
  ArrowRight, ToggleLeft, ToggleRight, AlertCircle, Loader2, Check 
} from 'lucide-react';
import { apiUrl } from '../lib/api';

const Upload = () => {
  const [modelFile, setModelFile] = useState(null);
  const [datasetFile, setDatasetFile] = useState(null);
  const [targetColumn, setTargetColumn] = useState('');
  const [protectedAttribute, setProtectedAttribute] = useState('');
  const [columns, setColumns] = useState([]);
  const [features, setFeatures] = useState([]); // List of { feature_name, known_at_prediction_time }
  
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // Handle CSV upload to extract column names
  const handleDatasetChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setDatasetFile(file);
    setError('');
    setLoadingPreview(true);
    setColumns([]);
    setFeatures([]);

    const formData = new FormData();
    formData.append('dataset_file', file);

    const token = localStorage.getItem('access_token');

    try {
      const response = await fetch(apiUrl('/api/audits/preview-dataset/'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        setColumns(data.columns);
        // Default target column to the last column
        if (data.columns.length > 0) {
          const defaultTarget = data.columns[data.columns.length - 1];
          setTargetColumn(defaultTarget);
          updateFeatureList(data.columns, defaultTarget);
        }
      } else {
        setError(data.error || 'Failed to parse the dataset columns.');
        setDatasetFile(null);
      }
    } catch (err) {
      setError('Connection failure. Django API server could not be reached.');
      setDatasetFile(null);
    } finally {
      setLoadingPreview(false);
    }
  };

  // Helper to sync feature toggle configurations when target column changes
  const updateFeatureList = (allCols, selectedTarget) => {
    const remainingFeatures = allCols
      .filter(col => col !== selectedTarget)
      .map(col => ({
        feature_name: col,
        known_at_prediction_time: true
      }));
    setFeatures(remainingFeatures);
  };

  const handleTargetChange = (e) => {
    const selected = e.target.value;
    setTargetColumn(selected);
    updateFeatureList(columns, selected);
  };

  const toggleFeatureKnown = (index) => {
    const updated = [...features];
    updated[index].known_at_prediction_time = !updated[index].known_at_prediction_time;
    setFeatures(updated);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!modelFile || !datasetFile || !targetColumn) {
      setError('Please select a model, a dataset, and target column to evaluate.');
      return;
    }

    setError('');
    setSubmitting(true);

    const formData = new FormData();
    formData.append('model_file', modelFile);
    formData.append('dataset_file', datasetFile);
    formData.append('target_column', targetColumn);
    if (protectedAttribute) {
      formData.append('protected_attribute', protectedAttribute);
    }
    // Append features configuration as a JSON string
    formData.append('features', JSON.stringify(features));

    const token = localStorage.getItem('access_token');

    try {
      const response = await fetch(apiUrl('/api/audits/'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.ok ? await response.json() : null;

      if (response.ok && data) {
        navigate(`/job/${data.id}`);
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.error || 'Failed to start audit job. Ensure files are not corrupted.');
      }
    } catch (err) {
      setError('Unable to submit audit request. Check server connection.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#1A1220] text-slate-100 flex flex-col font-sans relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-10 left-10 w-[500px] h-[500px] bg-pink-900/10 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-10 right-10 w-[500px] h-[500px] bg-violet-900/10 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Header */}
      <header className="border-b border-[#3D2F42] bg-[#1F1522]/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white leading-tight font-display">
              Model<span className="text-rose-400">Doctor</span>
            </h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">New Audit Job</p>
          </div>
        </div>
        <button 
          onClick={() => navigate('/')}
          className="text-xs text-slate-400 hover:text-white border border-slate-800 hover:border-slate-700 px-3 py-1.5 rounded-lg transition-all"
        >
          Back to Dashboard
        </button>
      </header>

      {/* Main Upload Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 space-y-6 relative z-10">
        
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight text-white font-display">Create Evaluation Run</h2>
          <p className="text-xs text-slate-400">Upload your serialized classifier or regressor along with evaluation dataset to execute diagnostic validation tasks.</p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3 text-red-200 text-sm">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* File Picker Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Model Upload File Container */}
            <div className="glass-panel rounded-xl p-5 border border-slate-800 flex flex-col justify-between min-h-[220px]">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <FileCode className="w-5 h-5 text-rose-400" />
                  <h3 className="text-sm font-semibold text-white">Model File (.pkl / .joblib)</h3>
                </div>
                <p className="text-xs text-slate-400">Upload your saved Scikit-Learn model binary.</p>
              </div>

              <div className="mt-4">
                <label className="relative flex flex-col items-center justify-center border border-dashed border-[#3D2F42] hover:border-rose-500/40 bg-[#1F1522]/40 hover:bg-[#1F1522]/60 rounded-xl p-6 cursor-pointer transition-all">
                  {modelFile ? (
                    <div className="text-center">
                      <div className="w-10 h-10 rounded-full bg-rose-500/10 flex items-center justify-center mx-auto mb-2">
                        <Check className="w-5 h-5 text-rose-400" />
                      </div>
                      <span className="text-xs text-slate-200 block truncate max-w-[250px] font-semibold">{modelFile.name}</span>
                      <span className="text-[10px] text-slate-500 mt-1 block">{(modelFile.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ) : (
                    <div className="text-center space-y-1">
                      <span className="text-xs text-rose-400 font-semibold hover:underline">Select model binary</span>
                      <span className="text-[10px] text-slate-500 block">Accepts .joblib, .pkl</span>
                    </div>
                  )}
                  <input
                    type="file"
                    required
                    accept=".pkl,.joblib"
                    onChange={(e) => setModelFile(e.target.files[0])}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* Dataset Upload File Container */}
            <div className="glass-panel rounded-xl p-5 border border-slate-800 flex flex-col justify-between min-h-[220px]">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <FileSpreadsheet className="w-5 h-5 text-violet-400" />
                  <h3 className="text-sm font-semibold text-white">Dataset File (.csv)</h3>
                </div>
                <p className="text-xs text-slate-400">Upload evaluation data to check statistics and fairness constraints.</p>
              </div>

              <div className="mt-4">
                <label className="relative flex flex-col items-center justify-center border border-dashed border-[#3D2F42] hover:border-violet-500/40 bg-[#1F1522]/40 hover:bg-[#1F1522]/60 rounded-xl p-6 cursor-pointer transition-all">
                  {loadingPreview ? (
                    <div className="text-center">
                      <Loader2 className="w-6 h-6 text-violet-400 animate-spin mx-auto mb-2" />
                      <span className="text-xs text-slate-400">Parsing column headers...</span>
                    </div>
                  ) : datasetFile ? (
                    <div className="text-center">
                      <div className="w-10 h-10 rounded-full bg-violet-500/10 flex items-center justify-center mx-auto mb-2">
                        <Check className="w-5 h-5 text-violet-400" />
                      </div>
                      <span className="text-xs text-slate-200 block truncate max-w-[250px] font-semibold">{datasetFile.name}</span>
                      <span className="text-[10px] text-slate-500 mt-1 block">{(datasetFile.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ) : (
                    <div className="text-center space-y-1">
                      <span className="text-xs text-violet-400 font-semibold hover:underline">Select CSV file</span>
                      <span className="text-[10px] text-slate-500 block">Accepts .csv</span>
                    </div>
                  )}
                  <input
                    type="file"
                    required
                    accept=".csv"
                    onChange={handleDatasetChange}
                    className="hidden"
                    disabled={loadingPreview}
                  />
                </label>
              </div>
            </div>

          </div>

          {/* Config parameters displayed only after column headers are loaded */}
          {columns.length > 0 && (
            <div className="glass-panel rounded-xl p-6 border border-slate-800 space-y-6">
              
              {/* Select target */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Target Label Variable
                </label>
                <p className="text-[11px] text-slate-500 mb-3">Choose the columns representing the ground-truth prediction target.</p>
                <select
                  value={targetColumn}
                  onChange={handleTargetChange}
                  className="w-full md:w-1/2 bg-[#1F1522]/60 border border-[#3D2F42] rounded-lg p-2.5 text-white outline-none focus:border-rose-500/50 text-sm transition-all"
                >
                  {columns.map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              {/* Select protected attribute */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Protected Attribute Variable (Optional)
                </label>
                <p className="text-[11px] text-slate-500 mb-3">Choose a feature to audit fairness metrics (e.g. demographic parity, equalised odds difference).</p>
                <select
                  value={protectedAttribute}
                  onChange={(e) => setProtectedAttribute(e.target.value)}
                  className="w-full md:w-1/2 bg-[#1F1522]/60 border border-[#3D2F42] rounded-lg p-2.5 text-white outline-none focus:border-rose-500/50 text-sm transition-all"
                >
                  <option value="">-- None / Skip Fairness Audit --</option>
                  {columns.filter(col => col !== targetColumn).map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              {/* Toggles for features known at prediction time */}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Feature Metadata Parameters
                  </label>
                  <p className="text-[11px] text-slate-500 mt-0.5">Toggle features that will be explicitly known during prediction execution (used for data quality metrics).</p>
                </div>

                <div className="border border-slate-900 rounded-lg overflow-hidden max-h-[300px] overflow-y-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-950/50 border-b border-slate-900 text-slate-400">
                        <th className="p-3">Feature Name</th>
                        <th className="p-3 text-right">Known at Prediction Time</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900">
                      {features.map((feat, idx) => (
                        <tr key={feat.feature_name} className="hover:bg-slate-950/20 text-slate-300">
                          <td className="p-3 font-mono font-medium">{feat.feature_name}</td>
                          <td className="p-3 text-right">
                            <button
                              type="button"
                              onClick={() => toggleFeatureKnown(idx)}
                              className="text-slate-400 hover:text-white transition-colors"
                            >
                              {feat.known_at_prediction_time ? (
                                <span className="flex items-center gap-1 text-emerald-400 justify-end font-semibold">
                                  Yes <ToggleRight className="w-5 h-5 text-emerald-400" />
                                </span>
                              ) : (
                                <span className="flex items-center gap-1 text-slate-500 justify-end font-semibold">
                                  No <ToggleLeft className="w-5 h-5 text-slate-600" />
                                </span>
                              )}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Submit triggers */}
              <div className="pt-4 border-t border-slate-900 flex justify-end">
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-gradient-to-r from-rose-500 to-fuchsia-500 hover:from-rose-400 hover:to-fuchsia-400 text-white font-semibold text-sm px-6 py-2.5 rounded-lg flex items-center gap-2 transition-all disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Executing Pipeline...
                    </>
                  ) : (
                    <>
                      Trigger Audit
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

            </div>
          )}

        </form>
      </main>
    </div>
  );
};

export default Upload;
