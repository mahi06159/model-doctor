import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiUrl } from '../lib/api';
import {
  ShieldAlert, Loader2, AlertCircle, CheckCircle,
  Database, RefreshCw, User, Info, FileSpreadsheet, ArrowLeft,
  ChevronDown, ChevronUp, AlertTriangle, TrendingUp, Sparkles, Scale, Activity, Download, Upload, Shield
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

const JobStatus = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('quality');
  const [expandedFeatures, setExpandedFeatures] = useState({});
  const [showCorrelationInfo, setShowCorrelationInfo] = useState(false);
  const [uploadingDrift, setUploadingDrift] = useState(false);
  const [driftError, setDriftError] = useState('');
  const fileInputRef = React.useRef(null);

  const handleProductionUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingDrift(true);
    setDriftError('');

    const formData = new FormData();
    formData.append('production_dataset_file', file);

    const token = localStorage.getItem('access_token');
    try {
      const response = await fetch(apiUrl(`/api/audits/${id}/upload-production/`), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        // Trigger job details reload
        fetchJobDetails();
      } else {
        setDriftError(data.error || 'Failed to upload production dataset.');
      }
    } catch (err) {
      setDriftError('Failed to connect to the server.');
    } finally {
      setUploadingDrift(false);
    }
  };

  useEffect(() => {
    fetchJobDetails();

    // Poll every 2 seconds if pending or processing
    const interval = setInterval(() => {
      checkPollingStatus();
    }, 2000);

    return () => clearInterval(interval);
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchJobDetails = async () => {
    const isDemo = String(id).startsWith('demo-');
    const url = isDemo ? `/api/demo-audits/${id}/` : `/api/audits/${id}/`;
    const headers = { 'Content-Type': 'application/json' };

    if (!isDemo) {
      const token = localStorage.getItem('access_token');
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(apiUrl(url), { headers });

      if (response.ok) {
        const data = await response.json();
        setJob(data);
      } else {
        setError('Failed to fetch job status details.');
      }
    } catch (err) {
      setError('Unable to reach the backend server.');
    } finally {
      setLoading(false);
    }
  };

  const checkPollingStatus = () => {
    if (!job) return;
    if (job.status === 'PENDING' || job.status === 'PROCESSING') {
      fetchJobDetails();
    }
  };

  const toggleFeature = (name) => {
    setExpandedFeatures(prev => ({
      ...prev,
      [name]: !prev[name]
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#1A1220] text-slate-100 flex items-center justify-center">
        <div className="text-center space-y-3">
          <Loader2 className="w-10 h-10 animate-spin text-rose-500 mx-auto" />
          <p className="text-sm text-slate-400">Loading audit status...</p>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-[#1A1220] text-slate-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full glass-panel border-red-500/20 rounded-2xl p-6 text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
          <h3 className="text-lg font-bold text-white">Error Encountered</h3>
          <p className="text-xs text-slate-400">{error || 'Job not found.'}</p>
          <button
            onClick={() => navigate('/')}
            className="bg-slate-900 border border-slate-800 hover:bg-slate-800 px-4 py-2 rounded-lg text-xs font-semibold"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const isPending = job.status === 'PENDING';
  const isProcessing = job.status === 'PROCESSING';
  const isCompleted = job.status === 'COMPLETED';
  const isFailed = job.status === 'FAILED';

  // Formatting and parsing completed results
  let missingChartData = [];
  let outlierChartData = [];
  let columnGridList = [];

  let leakageList = job.leakage_results || [];
  let leakageChartData = [];
  let flaggedLeakageCount = 0;
  let maxLeakageRisk = 0.0;
  let visibilityFlagsCount = 0;

  let calibrationData = null;
  let overfittingData = null;
  let featureDominanceData = null;

  if (isCompleted && job.results) {
    const results = job.results;

    // 1. Data Quality formatting
    missingChartData = Object.entries(results.missing_data || {}).map(([col, info]) => ({
      name: col,
      missing_pct: info.percentage
    })).sort((a, b) => b.missing_pct - a.missing_pct);

    outlierChartData = Object.entries(results.outliers || {}).map(([col, info]) => ({
      name: col,
      outlier_count: info.count,
      outlier_pct: info.percentage
    })).filter(item => item.outlier_count > 0);

    const featuresMap = {};
    (job.features || []).forEach(f => {
      featuresMap[f.feature_name] = f.known_at_prediction_time;
    });

    columnGridList = Object.keys(results.missing_data || {}).map(col => {
      const isTarget = col === job.target_column;
      const known = isTarget ? 'Target' : (featuresMap[col] ?? true);
      const isOutlier = results.outliers?.[col];

      return {
        name: col,
        type: results.column_types?.[col] || 'Unknown',
        missingCount: results.missing_data?.[col]?.count ?? 0,
        missingPct: results.missing_data?.[col]?.percentage ?? 0,
        outlierCount: isOutlier ? isOutlier.count : '-',
        outlierPct: isOutlier ? isOutlier.percentage : '-',
        known: known
      };
    });

    // 2. Leakage formatting
    leakageChartData = leakageList.map(item => ({
      name: item.feature_name,
      risk_score: item.risk_score
    }));

    flaggedLeakageCount = leakageList.filter(item => item.risk_score > 50 || item.known_flag).length;
    if (leakageList.length > 0) {
      maxLeakageRisk = Math.max(...leakageList.map(item => item.risk_score));
    }
    visibilityFlagsCount = leakageList.filter(item => item.known_flag).length;

    // 3. Calibration formatting
    if (results.calibration && results.calibration.supported) {
      calibrationData = results.calibration;
    }

    // 4. Overfitting formatting
    if (results.overfitting && results.overfitting.supported) {
      overfittingData = results.overfitting;
    }

    // 5. Feature dominance formatting
    if (results.feature_dominance && results.feature_dominance.supported) {
      featureDominanceData = results.feature_dominance;
    }
  }

  return (
    <div className="min-h-screen bg-[#1A1220] text-slate-100 flex flex-col font-sans relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-10 left-10 w-[500px] h-[500px] bg-pink-900/10 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Top Navbar */}
      <header className="border-b border-[#3D2F42] bg-[#1F1522]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5 text-rose-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wide text-white font-display">
              Model<span className="text-rose-400">Doctor</span>
            </h1>
            <p className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold">Audit Job Status</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isCompleted && (
            <>
              <button
                id="download-report-btn"
                onClick={async () => {
                  const token = localStorage.getItem('access_token');
                  const isDemo = String(id).startsWith('demo-');
                  const url = `/api/audits/${id}/report/?filetype=pdf`;
                  const headers = {};
                  if (!isDemo) {
                    headers['Authorization'] = `Bearer ${token}`;
                  }
                  try {
                    const resp = await fetch(apiUrl(url), { headers });
                    if (!resp.ok) {
                      const errData = await resp.json().catch(() => ({}));
                      alert(errData.error || 'Failed to download report.');
                      return;
                    }
                    const blob = await resp.blob();
                    const downloadUrl = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = `modeldoctor_report_${id.slice(0, 8)}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    URL.revokeObjectURL(downloadUrl);
                    document.body.removeChild(a);
                  } catch (err) {
                    alert('Unable to connect to the server to download report.');
                  }
                }}
                className="flex items-center gap-1.5 text-xs bg-[#1F1522] hover:bg-[#2A1F30] border border-[#3D2F42] hover:border-rose-500/30 text-slate-350 px-3.5 py-2 rounded-lg transition-all font-semibold"
              >
                <Download className="w-3.5 h-3.5 text-rose-400" />
                Download PDF
              </button>
              <button
                id="download-docx-btn"
                onClick={async () => {
                  const token = localStorage.getItem('access_token');
                  const isDemo = String(id).startsWith('demo-');
                  const url = `/api/audits/${id}/report/?filetype=docx`;
                  const headers = {};
                  if (!isDemo) {
                    headers['Authorization'] = `Bearer ${token}`;
                  }
                  try {
                    const resp = await fetch(apiUrl(url), { headers });
                    if (!resp.ok) {
                      const errData = await resp.json().catch(() => ({}));
                      alert(errData.error || 'Failed to download report.');
                      return;
                    }
                    const blob = await resp.blob();
                    const downloadUrl = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = `modeldoctor_report_${id.slice(0, 8)}.docx`;
                    document.body.appendChild(a);
                    a.click();
                    URL.revokeObjectURL(downloadUrl);
                    document.body.removeChild(a);
                  } catch (err) {
                    alert('Unable to connect to the server to download report.');
                  }
                }}
                className="flex items-center gap-1.5 text-xs bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 hover:border-rose-500/60 text-rose-400 px-3.5 py-2 rounded-lg transition-all font-semibold"
              >
                <Download className="w-3.5 h-3.5" />
                Download Word Doc
              </button>
            </>
          )}
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-xs border border-slate-800 hover:border-slate-700 bg-slate-950 px-4 py-2 rounded-lg text-slate-300 font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Dashboard
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6 relative z-10">

        {/* Header Job Info */}
        <section className="glass-panel rounded-xl p-5 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-widest font-semibold mb-1">Audit Evaluation Job</div>
            <h2 className="text-lg font-bold text-white font-mono break-all">{job.id}</h2>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-400">
              <span className="flex items-center gap-1"><User className="w-3.5 h-3.5 text-slate-500" /> {job.username}</span>
              <span className="flex items-center gap-1"><Database className="w-3.5 h-3.5 text-slate-500" /> Target: <code className="bg-slate-950 px-1 py-0.5 rounded text-rose-400">{job.target_column}</code></span>
              <span className="flex items-center gap-1"><FileSpreadsheet className="w-3.5 h-3.5 text-slate-500" /> Created at: {new Date(job.created_at).toLocaleString()}</span>
            </div>
          </div>

          <div className="shrink-0 flex items-center">
            {isPending && (
              <span className="bg-amber-500/10 border border-amber-500/30 text-amber-400 px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                Pending Queue
              </span>
            )}
            {isProcessing && (
              <span className="bg-rose-500/10 border border-rose-500/30 text-rose-400 px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                Processing Audit...
              </span>
            )}
            {isCompleted && (
              <div className="flex flex-col items-end gap-2">
                <div className="flex items-center gap-2">
                  {job.results?.health_score && (
                    <div className="bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-2 text-center">
                      <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mb-0.5">Health Score</div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xl font-bold text-white">{job.results.health_score.score}</span>
                        <span className={`text-sm font-bold px-2 py-0.5 rounded-full border ${job.results.health_score.grade === 'A' ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' :
                            job.results.health_score.grade === 'B' ? 'text-rose-400 border-rose-500/30 bg-rose-500/10' :
                              job.results.health_score.grade === 'C' ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' :
                                'text-red-400 border-red-500/30 bg-red-500/10'
                          }`}>{job.results.health_score.grade}</span>
                      </div>
                    </div>
                  )}
                  <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-1.5">
                    <CheckCircle className="w-4 h-4" />
                    Audit Completed
                  </span>
                </div>

                {/* Upload Production Data Section */}
                <div className="flex flex-col items-end gap-1">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingDrift}
                    className="flex items-center gap-1.5 text-xs bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/30 hover:border-violet-500/60 text-violet-400 px-3 py-1.5 rounded-lg transition-all font-semibold disabled:opacity-50"
                  >
                    {uploadingDrift ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Upload className="w-3.5 h-3.5" />
                    )}
                    {uploadingDrift ? 'Uploading...' : job.results?.drift ? 'Update Production Data' : 'Upload Production Data'}
                  </button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleProductionUpload}
                    accept=".csv"
                    className="hidden"
                  />
                  {driftError && (
                    <span className="text-[10px] text-red-400 font-medium">{driftError}</span>
                  )}
                  {job.results?.drift && (
                    <span className="text-[9px] text-emerald-400 flex items-center gap-1 mt-0.5">
                      <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse"></span>
                      Production Data Loaded
                    </span>
                  )}
                </div>
              </div>
            )}
            {isFailed && (
              <span className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" />
                Audit Failed
              </span>
            )}
          </div>
        </section>

        {/* PROCESSING & PENDING LOADER VIEW */}
        {/* PROCESSING & PENDING LOADER VIEW */}
        {(isPending || isProcessing) && (() => {
          const progressPercent = job.results?.progress?.percent || (isPending ? 5 : 15);
          const progressMsg = job.results?.progress?.message || "Initializing audit run...";

          const stages = [
            { id: 'quality', label: 'Data Quality Check', minPct: 15 },
            { id: 'leakage', label: 'Target Leakage Diagnostics', minPct: 35 },
            { id: 'calibration', label: 'Probability Calibration Analysis', minPct: 55 },
            { id: 'overfitting', label: 'Overfitting & Learning Curves', minPct: 70 },
            { id: 'dominance', label: 'Global Feature Dominance (SHAP)', minPct: 80 },
            { id: 'fairness', label: 'Algorithmic Fairness Evaluation', minPct: 90 },
          ];

          return (
            <section className="glass-panel rounded-xl border border-slate-800/80 p-8 flex flex-col md:flex-row gap-8 items-center min-h-[350px]">

              {/* Left Side: Spinner + Gauge Bar */}
              <div className="flex-1 flex flex-col items-center justify-center space-y-4 w-full">
                <div className="relative">
                  <div className="w-20 h-20 rounded-full border border-rose-500/20 absolute -top-2 -left-2 animate-ping opacity-75"></div>
                  <div className="w-16 h-16 rounded-full border-2 border-slate-800 border-t-rose-500 animate-spin flex items-center justify-center">
                    <ShieldAlert className="w-6 h-6 text-rose-400" />
                  </div>
                </div>

                <div className="w-full text-center space-y-1.5">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">Audit Progress: {progressPercent}%</h3>
                  <p className="text-xs text-rose-400 font-mono italic">{progressMsg}</p>
                </div>

                {/* Progress bar */}
                <div className="w-full max-w-sm bg-slate-950/80 border border-slate-850 h-2.5 rounded-full overflow-hidden">
                  <div
                    className="bg-rose-500 h-full rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              {/* Right Side: Step Checklist */}
              <div className="flex-1 w-full space-y-3 border-t md:border-t-0 md:border-l border-[#3D2F42] pt-6 md:pt-0 md:pl-8">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Diagnostic Stages</h4>
                <div className="space-y-2">
                  {stages.map((stg) => {
                    const isCompleted = progressPercent > stg.minPct;
                    const isActive = progressPercent <= stg.minPct && (stages.find(s => progressPercent <= s.minPct)?.id === stg.id);
                    return (
                      <div key={stg.id} className="flex items-center gap-3 text-xs">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 border transition-all ${isCompleted ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                            isActive ? 'bg-rose-500/10 border-rose-500/30 text-rose-400 animate-pulse' :
                              'bg-slate-950/40 border-[#3D2F42] text-slate-650'
                          }`}>
                          {isCompleted ? <CheckCircle className="w-3.5 h-3.5" /> : <span className="text-[10px]">•</span>}
                        </div>
                        <span className={`${isCompleted ? 'text-slate-350 line-through decoration-slate-850' :
                            isActive ? 'text-rose-400 font-semibold animate-pulse' :
                              'text-slate-500'
                          }`}>{stg.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

            </section>
          );
        })()}

        {/* FAILED VIEW */}
        {isFailed && (
          <section className="glass-panel rounded-xl border border-red-500/20 bg-red-500/[0.02] p-8 space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-center shrink-0">
                <AlertCircle className="w-5 h-5 text-red-400" />
              </div>
              <div className="space-y-1">
                <h3 className="text-md font-bold text-white">Execution Failure Report</h3>
                <p className="text-xs text-slate-400">
                  The analysis engine crashed during processing. Verify that the features dataset file structure perfectly matches.
                </p>
              </div>
            </div>

            <div className="bg-slate-950/80 rounded-xl p-4 border border-[#3D2F42] font-mono text-xs text-red-300 min-h-[100px] leading-relaxed break-all">
              {job.error_message || "No error traceback was recorded."}
            </div>
          </section>
        )}

        {/* COMPLETED RESULTS DISPLAY */}
        {isCompleted && job.results && (
          <div className="space-y-6 animate-fade-in">

            {/* Tabs Navigation Header */}
            <div className="flex border-b border-[#3D2F42] gap-6">
              <button
                onClick={() => setActiveTab('quality')}
                className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${activeTab === 'quality' ? 'text-rose-400' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Database className="w-4 h-4" />
                Data Quality
                {activeTab === 'quality' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-500 rounded-full"></span>}
              </button>

              <button
                onClick={() => setActiveTab('leakage')}
                className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${activeTab === 'leakage' ? 'text-rose-400' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <ShieldAlert className="w-4 h-4" />
                Leakage Report
                {flaggedLeakageCount > 0 && (
                  <span className="bg-red-500 text-white text-[9px] px-1.5 py-0.2 rounded-full font-bold">
                    {flaggedLeakageCount}
                  </span>
                )}
                {activeTab === 'leakage' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-500 rounded-full"></span>}
              </button>

              <button
                onClick={() => setActiveTab('calibration')}
                className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${activeTab === 'calibration' ? 'text-rose-400' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Scale className="w-4 h-4" />
                Model Calibration
                {activeTab === 'calibration' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-500 rounded-full"></span>}
              </button>

              <button
                onClick={() => setActiveTab('overfitting')}
                className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${activeTab === 'overfitting' ? 'text-rose-400' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Activity className="w-4 h-4" />
                Overfitting & SHAP
                {activeTab === 'overfitting' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-500 rounded-full"></span>}
              </button>

              <button
                onClick={() => setActiveTab('fairness')}
                className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${activeTab === 'fairness' ? 'text-rose-400' : 'text-slate-400 hover:text-slate-200'}`}
              >
                <Shield className="w-4 h-4" />
                Fairness
                {activeTab === 'fairness' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-500 rounded-full"></span>}
              </button>

              {job.results?.drift && (
                <button
                  onClick={() => setActiveTab('drift')}
                  className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${activeTab === 'drift' ? 'text-rose-400' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  <TrendingUp className="w-4 h-4" />
                  Data Drift
                  {activeTab === 'drift' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-500 rounded-full"></span>}
                </button>
              )}
            </div>

            {/* TAB CONTENTS */}

            {/* 1. DATA QUALITY TAB */}
            {activeTab === 'quality' && (
              <div className="space-y-6">
                {/* Stats Summary cards */}
                <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="glass-panel rounded-xl p-5 border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-2">Dataset Rows</div>
                    <div className="text-2xl font-black text-white">{job.results.total_rows.toLocaleString()}</div>
                    <p className="text-[9px] text-slate-500 mt-1">Total row records analyzed</p>
                  </div>

                  <div className="glass-panel rounded-xl p-5 border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-2">Evaluated Features</div>
                    <div className="text-2xl font-black text-white">{job.results.total_columns - 1}</div>
                    <p className="text-[9px] text-slate-500 mt-1">Excludes target column</p>
                  </div>

                  <div className="glass-panel rounded-xl p-5 border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-2">Duplicate Rows</div>
                    <div className="text-2xl font-black text-white">
                      {job.results.duplicates.count.toLocaleString()}
                    </div>
                    <p className="text-[9px] text-slate-500 mt-1">
                      ({job.results.duplicates.percentage}% of total dataset)
                    </p>
                  </div>

                  <div className="glass-panel rounded-xl p-5 border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-2">Data Quality Score</div>
                    <div className="text-2xl font-black text-emerald-400">
                      {Math.max(0, 100 - Object.values(job.results.missing_data).reduce((acc, curr) => acc + (curr.percentage > 0 ? 1 : 0), 0) * 5 - (job.results.duplicates.count > 0 ? 10 : 0))}%
                    </div>
                    <p className="text-[9px] text-slate-500 mt-1">Weighted quality metrics profile</p>
                  </div>
                </section>

                {/* Data Quality Charts */}
                <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Missing Data Chart */}
                  <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Missing Values Profile (%)</h3>
                      <p className="text-[11px] text-slate-400">Percentage of missing/null items sorted per column</p>
                    </div>

                    <div className="h-60 w-full">
                      {missingChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={missingChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <XAxis dataKey="name" stroke="#64748B" fontSize={10} tickLine={false} />
                            <YAxis stroke="#64748B" fontSize={10} tickLine={false} unit="%" />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#2A1F30', borderColor: '#3D2F42', borderRadius: 8, color: '#F1F5F9' }}
                            />
                            <Bar dataKey="missing_pct" fill="#F472B6" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-xs text-slate-500">No missing data detected.</div>
                      )}
                    </div>
                  </div>

                  {/* Outliers Chart */}
                  <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Numerical Outliers (IQR)</h3>
                      <p className="text-[11px] text-slate-400">Number of values falling outside IQR limits</p>
                    </div>

                    <div className="h-60 w-full">
                      {outlierChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={outlierChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <XAxis dataKey="name" stroke="#64748B" fontSize={10} tickLine={false} />
                            <YAxis stroke="#64748B" fontSize={10} tickLine={false} />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#2A1F30', borderColor: '#3D2F42', borderRadius: 8, color: '#F1F5F9' }}
                            />
                            <Bar dataKey="outlier_count" fill="#C084FC" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-xs text-slate-500">No outliers detected in numeric variables.</div>
                      )}
                    </div>
                  </div>
                </section>

                {/* Detailed Features List */}
                <section className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4">
                  <div>
                    <h3 className="text-md font-bold text-white">Detailed Feature Validation Profiles</h3>
                    <p className="text-xs text-slate-400">Full audit list of dataset features mapping types, null rates, IQR outliers, and forecasting visibility configurations.</p>
                  </div>

                  <div className="border border-[#3D2F42] rounded-lg overflow-hidden font-sans">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-950/80 border-b border-[#3D2F42] text-slate-400">
                          <th className="p-3">Column Name</th>
                          <th className="p-3">Inferred Type</th>
                          <th className="p-3">Missing Rate</th>
                          <th className="p-3">Outlier Counts</th>
                          <th className="p-3 text-right">Visibility</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-900">
                        {columnGridList.map((col) => {
                          const isTarget = col.known === 'Target';
                          const isKnown = col.known === true;

                          return (
                            <tr key={col.name} className="hover:bg-slate-950/20 text-slate-300 font-mono">
                              <td className="p-3 font-semibold text-white break-all">{col.name}</td>
                              <td className="p-3 text-slate-400">{col.type}</td>
                              <td className="p-3">
                                <span className={col.missingCount > 0 ? "text-amber-400 font-semibold" : "text-slate-400"}>
                                  {col.missingCount.toLocaleString()} ({col.missingPct}%)
                                </span>
                              </td>
                              <td className="p-3">
                                <span className={col.outlierCount > 0 ? "text-violet-400 font-semibold" : "text-slate-400"}>
                                  {col.outlierCount} {col.outlierPct !== '-' ? `(${col.outlierPct}%)` : ''}
                                </span>
                              </td>
                              <td className="p-3 text-right font-sans">
                                {isTarget ? (
                                  <span className="bg-rose-500/10 border border-rose-500/30 text-rose-400 px-2 py-0.5 rounded text-[10px] font-bold">
                                    Target Column
                                  </span>
                                ) : isKnown ? (
                                  <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-2 py-0.5 rounded text-[10px] font-medium">
                                    Prediction Time
                                  </span>
                                ) : (
                                  <span className="bg-slate-800 border border-slate-700 text-slate-400 px-2 py-0.5 rounded text-[10px] font-medium">
                                    Training Only
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
            )}

            {/* 2. LEAKAGE REPORT TAB */}
            {activeTab === 'leakage' && (
              <div className="space-y-6">

                {/* Stats Summary cards */}
                <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="glass-panel rounded-xl p-5 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Leaky Features Flagged</div>
                      <div className="text-2xl font-black text-white">{flaggedLeakageCount}</div>
                      <p className="text-[9px] text-slate-500 mt-1">High risk (&gt;50% score or unknown visibility)</p>
                    </div>
                    {flaggedLeakageCount > 0 ? (
                      <AlertTriangle className="w-8 h-8 text-amber-500 opacity-80" />
                    ) : (
                      <CheckCircle className="w-8 h-8 text-emerald-500 opacity-80" />
                    )}
                  </div>

                  <div className="glass-panel rounded-xl p-5 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Max Leakage Risk Score</div>
                      <div className={`text-2xl font-black ${maxLeakageRisk > 50 ? 'text-red-400' : maxLeakageRisk > 15 ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {maxLeakageRisk.toFixed(1)}%
                      </div>
                      <p className="text-[9px] text-slate-500 mt-1">Highest individual risk score computed</p>
                    </div>
                    <TrendingUp className="w-8 h-8 text-violet-500 opacity-80" />
                  </div>

                  <div className="glass-panel rounded-xl p-5 border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Prediction Visibility Violations</div>
                      <div className="text-2xl font-black text-white">{visibilityFlagsCount}</div>
                      <p className="text-[9px] text-slate-500 mt-1">Unknown at prediction time with high use</p>
                    </div>
                    <ShieldAlert className="w-8 h-8 text-red-500 opacity-80" />
                  </div>
                </section>

                <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Leakage Horizontal Chart */}
                  <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4 lg:col-span-2">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Target Leakage Risk Scores</h3>
                      <p className="text-[11px] text-slate-400">Fuzzy-OR combined score of retraining drop, SHAP dominance, and visibility validation</p>
                    </div>

                    <div className="h-64 w-full">
                      {leakageChartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={leakageChartData} layout="vertical" margin={{ top: 10, right: 20, left: 30, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#3D2F42" horizontal={false} />
                            <XAxis type="number" stroke="#64748B" fontSize={10} tickLine={false} domain={[0, 100]} unit="%" />
                            <YAxis dataKey="name" type="category" stroke="#64748B" fontSize={10} tickLine={false} width={100} />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#2A1F30', borderColor: '#3D2F42', borderRadius: 8, color: '#F1F5F9' }}
                            />
                            <Bar dataKey="risk_score" fill="#FBBF24" radius={[0, 4, 4, 0]} barSize={12} />
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="h-full flex items-center justify-center text-xs text-slate-500">No features analyzed.</div>
                      )}
                    </div>
                  </div>

                  {/* Interview Focus / Why not simple correlation */}
                  <div className="glass-panel rounded-xl p-5 border border-slate-800 flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-white">
                        <Sparkles className="w-5 h-5 text-yellow-400" />
                        <h3 className="text-sm font-bold">Interview Focus: Diagnostics</h3>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        In ML engineering interviews, you are often asked: <strong>&quot;Why not use Pearson correlation coefficients to detect target leakage?&quot;</strong>
                      </p>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        Correlation fails on 3 critical vectors: non-linear transformations (e.g. hashed leakage values or mathematical boundaries), multi-feature combinatorial leakage interactions, and true model integration context.
                      </p>
                    </div>

                    <button
                      onClick={() => setShowCorrelationInfo(!showCorrelationInfo)}
                      className="w-full text-center py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-xs font-semibold rounded-lg text-slate-200"
                    >
                      {showCorrelationInfo ? "Hide Full Answer Details" : "Read Full Interview Response"}
                    </button>
                  </div>
                </section>

                {/* Educational expand block */}
                {showCorrelationInfo && (
                  <div className="glass-panel rounded-xl p-5 border border-rose-500/20 bg-rose-500/[0.01] animate-fade-in space-y-3">
                    <h4 className="text-xs font-bold text-rose-400 uppercase tracking-wider">Interview Question: Why Model-in-the-Loop diagnostics beats Correlation</h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      &quot;While Pearson correlation is useful for finding simple collinearity, it fails to identify target leaks in complex settings.
                      First, correlation assumes a linear relationship. If a feature contains leaked target information passed through a non-linear function (e.g. integer bounds, logs, conditional hashes, or time differences), correlation can be near zero.
                      Second, correlation is computed feature-by-feature. It completely misses interactive leaks where two features must combine to leak the target.
                      Third, correlation ignores the actual model. Our algorithm clones the model and retrains it, computing SHAP values directly. This captures whether the model actually leverages the leak to predict, providing a direct diagnostic of predictive risk.&quot;
                    </p>
                  </div>
                )}

                {/* Detailed Features List with Dropdowns */}
                <section className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4">
                  <div>
                    <h3 className="text-md font-bold text-white font-sans">Multi-Signal Feature Diagnostics</h3>
                    <p className="text-xs text-slate-400 font-sans">Inspect individual feature risk scores, model performance drop upon feature exclusion, SHAP importance ratios, and visibility checks.</p>
                  </div>

                  <div className="space-y-3 font-mono">
                    {leakageList.map((item) => {
                      const isExpanded = !!expandedFeatures[item.feature_name];
                      const isHigh = item.risk_score > 50.0;
                      const isMed = item.risk_score > 15.0 && item.risk_score <= 50.0;

                      let badgeColor = "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
                      if (isHigh) badgeColor = "bg-red-500/10 border-red-500/30 text-red-400";
                      else if (isMed) badgeColor = "bg-amber-500/10 border-amber-500/30 text-amber-400";

                      return (
                        <div key={item.feature_name} className="border border-[#3D2F42] rounded-lg overflow-hidden bg-slate-950/20">
                          {/* Row Header */}
                          <div
                            onClick={() => toggleFeature(item.feature_name)}
                            className="p-3 flex items-center justify-between cursor-pointer hover:bg-slate-900/30 transition-all gap-4"
                          >
                            <div className="flex items-center gap-3">
                              <span className="font-semibold text-white text-xs sm:text-sm break-all">{item.feature_name}</span>
                              {item.known_flag && (
                                <span className="bg-red-500/10 border border-red-500/20 text-red-400 text-[9px] px-1.5 py-0.2 rounded font-bold uppercase">
                                  Unknown Visibility
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-3 shrink-0">
                              <span className={`border px-2 py-0.5 rounded text-xs font-semibold ${badgeColor}`}>
                                Risk: {item.risk_score.toFixed(1)}%
                              </span>
                              {isExpanded ? (
                                <ChevronUp className="w-4 h-4 text-slate-500" />
                              ) : (
                                <ChevronDown className="w-4 h-4 text-slate-500" />
                              )}
                            </div>
                          </div>

                          {/* Row Details (Collapsible) */}
                          {isExpanded && (
                            <div className="p-4 border-t border-[#3D2F42] bg-slate-950/50 space-y-3 font-sans text-xs text-slate-300">
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Signal 1: Retraining Drop</div>
                                  <div className="text-sm font-semibold text-white font-mono">{item.drop_pct.toFixed(2)}%</div>
                                  <p className="text-[9.5px] text-slate-400 mt-1">Relative performance loss when retrained without this feature. Flagged if &gt;15%.</p>
                                </div>

                                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Signal 2: SHAP Dominance</div>
                                  <div className="text-sm font-semibold text-white font-mono">
                                    {item.shap_ratio > 1.0 ? `${item.shap_ratio.toFixed(2)}x` : '-'}
                                  </div>
                                  <p className="text-[9.5px] text-slate-400 mt-1">Dominance ratio of SHAP values (top vs second-highest). Flagged if &gt;3x.</p>
                                </div>

                                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                                  <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Signal 3: Visibility Check</div>
                                  <div className="text-sm font-semibold text-white">
                                    {item.known_flag ? (
                                      <span className="text-red-400 font-semibold uppercase">Flagged Violation</span>
                                    ) : (
                                      <span className="text-emerald-400 font-medium">Valid Visibility</span>
                                    )}
                                  </div>
                                  <p className="text-[9.5px] text-slate-400 mt-1">Triggers if marked &apos;unknown at prediction time&apos; but has non-trivial importance.</p>
                                </div>
                              </div>

                              <div className="bg-[#1F1522] p-3 rounded-lg border border-[#3D2F42] flex items-start gap-2">
                                <Info className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                                <div>
                                  <h5 className="font-bold text-white text-[11px] mb-0.5">Audit Assessment Note</h5>
                                  <p className="text-[10px] text-slate-400 leading-relaxed">
                                    {isHigh ? (
                                      "Critical Leakage Risk: This feature shows high model-in-the-loop dominance or violates visibility constraints. Including it will likely result in overly optimistic test scores but total failure on real-time prediction environments."
                                    ) : isMed ? (
                                      "Moderate Importance: This feature contributes to model performance but does not show definitive characteristics of target leakage. Watch for downstream feature drift."
                                    ) : (
                                      "Low Risk: The feature shows mild or zero impact on model predictions and behaves cleanly in validation checks."
                                    )}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              </div>
            )}

            {/* 3. MODEL CALIBRATION TAB */}
            {activeTab === 'calibration' && (
              <div className="space-y-6">
                {calibrationData ? (
                  <>
                    {/* Brier score card */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="glass-panel rounded-xl p-5 border border-slate-800 flex items-center justify-between">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Brier Score Loss</div>
                          <div className="text-2xl font-black text-white">{calibrationData.brier_score}</div>
                          <p className="text-[9px] text-slate-500 mt-1">Lower is better. 0 represents perfect probability calibration.</p>
                        </div>
                        <Scale className="w-8 h-8 text-violet-500 opacity-80" />
                      </div>

                      <div className="glass-panel rounded-xl p-5 border border-slate-800 flex items-center justify-between">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Calibration Quality</div>
                          <div className="text-2xl font-black text-emerald-400">
                            {calibrationData.brier_score < 0.1 ? "Excellent" : calibrationData.brier_score < 0.25 ? "Moderate" : "Poor"}
                          </div>
                          <p className="text-[9px] text-slate-500 mt-1">Qualitative assessment of probability alignment</p>
                        </div>
                        {calibrationData.multiclass_target ? (
                          <div className="bg-slate-900 border border-slate-800 text-[10px] text-slate-400 px-2 py-1 rounded">
                            Target Class: {calibrationData.multiclass_target}
                          </div>
                        ) : null}
                      </div>
                    </div>

                    <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      {/* Reliability curve Line Chart */}
                      <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4 lg:col-span-2">
                        <div>
                          <h3 className="text-sm font-semibold text-white">Reliability Diagram</h3>
                          <p className="text-[11px] text-slate-400">Plots predicted probability bins vs actual outcome rates. Dashed line shows perfect calibration.</p>
                        </div>

                        <div className="h-64 w-full font-mono text-xs">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                              data={calibrationData.reliability_data}
                              margin={{ top: 10, right: 30, left: -20, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#3D2F42" />
                              <XAxis dataKey="pred_prob" stroke="#64748B" fontSize={10} label={{ value: 'Mean Predicted Probability', position: 'bottom', offset: 0, fill: '#64748B', fontSize: 10 }} />
                              <YAxis stroke="#64748B" fontSize={10} label={{ value: 'Fraction of Positives', angle: -90, position: 'left', offset: 10, fill: '#64748B', fontSize: 10 }} />
                              <Tooltip contentStyle={{ backgroundColor: '#2A1F30', borderColor: '#3D2F42', borderRadius: 8, color: '#F1F5F9' }} />
                              <Legend verticalAlign="top" height={36} />
                              {/* Reference diagonal line (ideal calibration) */}
                              <Line
                                name="Perfect Calibration"
                                type="monotone"
                                dataKey="pred_prob"
                                stroke="#475569"
                                strokeDasharray="5 5"
                                dot={false}
                                activeDot={false}
                              />
                              <Line
                                name="Model Probabilities"
                                type="monotone"
                                dataKey="actual_prob"
                                stroke="#F472B6"
                                strokeWidth={2}
                                dot={{ fill: '#F472B6', r: 4 }}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      {/* Educational info card */}
                      <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4 text-xs text-slate-300 flex flex-col justify-between">
                        <div className="space-y-2">
                          <h4 className="font-bold text-white text-sm flex items-center gap-1.5">
                            <Info className="w-4 h-4 text-rose-400" />
                            Probability Calibration Info
                          </h4>
                          <p className="leading-relaxed">
                            A model is calibrated when its predicted probabilities match empirical outcomes. For example, if a model assigns a probability of 0.8 to a set of predictions, 80% of those samples should actually belong to the positive class.
                          </p>
                          <p className="leading-relaxed">
                            <strong>Under-confidence:</strong> Curve lies above the diagonal. The model&apos;s predictions are less extreme than the actual probabilities.
                          </p>
                          <p className="leading-relaxed">
                            <strong>Over-confidence:</strong> Curve lies below the diagonal. The model predicts high probability values but actual conversion rates are much lower.
                          </p>
                        </div>
                      </div>
                    </section>
                  </>
                ) : (
                  <div className="glass-panel rounded-xl border border-slate-800 p-8 text-center text-xs text-slate-500">
                    Calibration metrics are not available for this job type. Requires a classification model supporting probability estimates.
                  </div>
                )}
              </div>
            )}

            {/* 5. FAIRNESS TAB */}
            {activeTab === 'fairness' && (
              <div className="space-y-6">
                {job.results?.fairness?.supported ? (
                  <>
                    <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="glass-panel rounded-xl p-5 border border-slate-800">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Demographic Parity Difference</div>
                        <div className="text-2xl font-black text-white">
                          {job.results.fairness.demographic_parity_difference.toFixed(4)}
                        </div>
                        <p className="text-[9px] text-slate-500 mt-1">Difference in selection rate between the highest and lowest groups.</p>
                      </div>

                      <div className="glass-panel rounded-xl p-5 border border-slate-800">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Equalized Odds Difference</div>
                        <div className="text-2xl font-black text-white">
                          {job.results.fairness.equalized_odds_difference.toFixed(4)}
                        </div>
                        <p className="text-[9px] text-slate-500 mt-1">Maximum difference in true positive rate or false positive rate across groups.</p>
                      </div>
                    </section>

                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 leading-relaxed">
                      <h4 className="font-bold mb-1">Normative Trade-offs Caveat</h4>
                      Fairness evaluation metrics involve inherent social and mathematical trade-offs. For example, enforcing demographic parity can conflict with predictive parity or model accuracy, meaning there is rarely a single &quot;correct&quot; answer. These results should be interpreted as empirical measurements to guide audits rather than strict pass/fail criteria.
                    </div>

                    <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4">
                      <div>
                        <h3 className="text-sm font-semibold text-white">Selection Rate & Error Rates by Group</h3>
                        <p className="text-[11px] text-slate-400">Positive outcome rates (predictions = 1) and true/false positive rates across different categories of the protected attribute <strong>{job.protected_attribute}</strong></p>
                      </div>

                      <div className="h-64 w-full font-mono text-xs">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={Object.entries(job.results.fairness.group_metrics || {}).map(([grp, m]) => ({
                              name: grp,
                              rate: m.selection_rate * 100,
                              tpr: m.tpr * 100,
                              fpr: m.fpr * 100
                            }))}
                            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#3D2F42" />
                            <XAxis dataKey="name" stroke="#64748B" fontSize={10} tickLine={false} />
                            <YAxis stroke="#64748B" fontSize={10} tickLine={false} unit="%" />
                            <Tooltip contentStyle={{ backgroundColor: '#2A1F30', borderColor: '#3D2F42', borderRadius: 8, color: '#F1F5F9' }} />
                            <Legend />
                            <Bar name="Selection Rate (%)" dataKey="rate" fill="#C084FC" radius={[4, 4, 0, 0]} />
                            <Bar name="True Positive Rate (%)" dataKey="tpr" fill="#4ADE80" radius={[4, 4, 0, 0]} />
                            <Bar name="False Positive Rate (%)" dataKey="fpr" fill="#F87171" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="glass-panel rounded-xl border border-slate-800 p-8 text-center text-xs text-slate-500">
                    {job.results?.fairness?.message || "Fairness analysis was not executed or is not supported for this job (e.g. no protected attribute selected)."}
                  </div>
                )}
              </div>
            )}

            {/* 6. DATA DRIFT TAB */}
            {activeTab === 'drift' && (
              <div className="space-y-6">
                {job.results?.drift?.supported ? (
                  <>
                    <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="glass-panel rounded-xl p-5 border border-slate-800">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Drifted Features</div>
                        <div className="text-2xl font-black text-white">
                          {job.results.drift.drifted_features_count} / {job.results.drift.total_features}
                        </div>
                        <p className="text-[9px] text-slate-500 mt-1">Number of features with PSI &gt; 0.2</p>
                      </div>

                      <div className="glass-panel rounded-xl p-5 border border-slate-800">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Drift Percentage</div>
                        <div className="text-2xl font-black text-white">
                          {job.results.drift.drift_percentage}%
                        </div>
                        <p className="text-[9px] text-slate-500 mt-1">Percentage of features showing significant drift.</p>
                      </div>

                      <div className="glass-panel rounded-xl p-5 border border-slate-800">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Status</div>
                        <div className={`text-2xl font-black ${job.results.drift.drifted_features_count > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                          {job.results.drift.drifted_features_count > 0 ? 'Drift Detected' : 'Stable'}
                        </div>
                        <p className="text-[9px] text-slate-500 mt-1">Threshold at Population Stability Index (PSI) of 0.2.</p>
                      </div>
                    </section>

                    <div className="glass-panel rounded-xl border border-slate-800/80 overflow-hidden">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-950/50 border-b border-[#3D2F42] text-slate-400">
                            <th className="p-3">Feature Name</th>
                            <th className="p-3">PSI Value</th>
                            <th className="p-3">KS-Test p-value</th>
                            <th className="p-3 text-right">Drift Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-900">
                          {Object.entries(job.results.drift.drift_by_feature || {}).map(([col, info]) => (
                            <tr key={col} className="hover:bg-slate-900/30">
                              <td className="p-3 font-semibold text-slate-200">{col}</td>
                              <td className="p-3 font-mono">{info.psi.toFixed(4)}</td>
                              <td className="p-3 font-mono">{info.ks_p_value !== null ? info.ks_p_value.toFixed(4) : '—'}</td>
                              <td className="p-3 text-right">
                                <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${info.drift_detected ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                  }`}>
                                  {info.drift_detected ? 'Drifted' : 'Stable'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <div className="glass-panel rounded-xl border border-slate-800 p-8 text-center text-xs text-slate-500">
                    {job.results?.drift?.message || "Drift analysis has not been executed yet. Upload production data above to run drift analysis."}
                  </div>
                )}
              </div>
            )}

            {/* 4. OVERFITTING & SHAP TAB */}
            {activeTab === 'overfitting' && (
              <div className="space-y-6">

                {overfittingData ? (
                  <>
                    {/* Diagnostic Summary Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="glass-panel rounded-xl p-5 border border-slate-800 flex items-center justify-between">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Performance Train/Val Gap</div>
                          <div className={`text-2xl font-black ${overfittingData.performance_gap > 0.15 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {overfittingData.performance_gap > 0 ? (overfittingData.performance_gap * 100).toFixed(1) : '0.0'}%
                          </div>
                          <p className="text-[9px] text-slate-500 mt-1">Difference between train and validation score at maximum sample size.</p>
                        </div>
                        <AlertTriangle className="w-8 h-8 text-amber-500 opacity-80" />
                      </div>

                      <div className="glass-panel rounded-xl p-5 border border-slate-800 flex items-center justify-between">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Cross-Validation Fold Variance</div>
                          <div className="text-2xl font-black text-white">{overfittingData.cv_variance}</div>
                          <p className="text-[9px] text-slate-500 mt-1">Score variance across CV folds. Low variance implies stable model fits.</p>
                        </div>
                        <Activity className="w-8 h-8 text-violet-500 opacity-80" />
                      </div>
                    </div>

                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* Learning curve Line Chart */}
                      <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4">
                        <div>
                          <h3 className="text-sm font-semibold text-white">Learning Curves</h3>
                          <p className="text-[11px] text-slate-400">Plots train vs validation {overfittingData.metric === 'accuracy' ? 'Accuracy' : 'R2'} scores across training dataset sizes.</p>
                        </div>

                        <div className="h-64 w-full font-mono text-xs">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                              data={overfittingData.learning_curve}
                              margin={{ top: 10, right: 30, left: -20, bottom: 5 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#3D2F42" />
                              <XAxis dataKey="train_size" stroke="#64748B" fontSize={10} label={{ value: 'Training Set Size', position: 'bottom', offset: 0, fill: '#64748B', fontSize: 10 }} />
                              <YAxis stroke="#64748B" fontSize={10} domain={['auto', 'auto']} />
                              <Tooltip contentStyle={{ backgroundColor: '#2A1F30', borderColor: '#3D2F42', borderRadius: 8, color: '#F1F5F9' }} />
                              <Legend verticalAlign="top" height={36} />
                              <Line
                                name="Training Score"
                                type="monotone"
                                dataKey="train_score"
                                stroke="#F87171"
                                strokeWidth={2}
                                dot={{ fill: '#F87171', r: 4 }}
                              />
                              <Line
                                name="Validation Score"
                                type="monotone"
                                dataKey="test_score"
                                stroke="#4ADE80"
                                strokeWidth={2}
                                dot={{ fill: '#4ADE80', r: 4 }}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      {/* Feature Dominance Chart (SHAP rankings) */}
                      <div className="glass-panel rounded-xl p-5 border border-slate-800 space-y-4">
                        <div>
                          <h3 className="text-sm font-semibold text-white">Global Feature Importance (SHAP)</h3>
                          <p className="text-[11px] text-slate-400">Average absolute SHAP importance rankings for all features.</p>
                        </div>

                        <div className="h-64 w-full font-mono text-xs">
                          {featureDominanceData && featureDominanceData.ranking && featureDominanceData.ranking.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart
                                data={featureDominanceData.ranking.slice(0, 10)}
                                layout="vertical"
                                margin={{ top: 5, right: 10, left: 30, bottom: 5 }}
                              >
                                <CartesianGrid strokeDasharray="3 3" stroke="#3D2F42" horizontal={false} />
                                <XAxis type="number" stroke="#64748B" fontSize={10} tickLine={false} />
                                <YAxis dataKey="feature_name" type="category" stroke="#64748B" fontSize={10} tickLine={false} width={100} />
                                <Tooltip contentStyle={{ backgroundColor: '#2A1F30', borderColor: '#3D2F42', borderRadius: 8, color: '#F1F5F9' }} />
                                <Bar dataKey="importance" fill="#C084FC" radius={[0, 4, 4, 0]} barSize={10} />
                              </BarChart>
                            </ResponsiveContainer>
                          ) : (
                            <div className="h-full flex items-center justify-center text-xs text-slate-500">No feature rankings computed.</div>
                          )}
                        </div>
                      </div>
                    </section>
                  </>
                ) : (
                  <div className="glass-panel rounded-xl border border-slate-800 p-8 text-center text-xs text-slate-500">
                    Overfitting diagnostics are not available for this job.
                  </div>
                )}

              </div>
            )}

          </div>
        )}

      </main>
    </div>
  );
};

export default JobStatus;