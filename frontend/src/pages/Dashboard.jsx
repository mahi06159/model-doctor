import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert, Activity, Cpu, LogOut, Plus,
  CheckCircle, AlertTriangle, Clock, Database,
  RefreshCw, ChevronRight, FileText, TrendingUp,
  Zap, Shield, BarChart2, AlertCircle, Download, Info
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Gauge SVG component — pure SVG arc, no extra library
// ---------------------------------------------------------------------------
const GaugeChart = ({ score, grade }) => {
  const r = 80;
  const cx = 110;
  const cy = 110;
  const startAngle = -210;
  const totalArc = 240; // degrees

  const gradeColors = {
    A: { track: '#4ADE80', glow: 'rgba(74,222,128,0.25)' },
    B: { track: '#F472B6', glow: 'rgba(244,114,182,0.25)' },
    C: { track: '#FBBF24', glow: 'rgba(251,191,36,0.25)' },
    D: { track: '#FB923C', glow: 'rgba(251,146,60,0.25)' },
    F: { track: '#F87171', glow: 'rgba(248,113,113,0.25)' },
  };
  const { track: trackColor, glow: glowColor } = gradeColors[grade] || gradeColors.F;

  const polar = (angle, radius) => {
    const rad = ((angle - 90) * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  };

  const arcPath = (from, to, radius) => {
    const s = polar(from, radius);
    const e = polar(to, radius);
    const large = to - from > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large} 1 ${e.x} ${e.y}`;
  };

  const fillAngle = startAngle + ((score / 100) * totalArc);

  return (
    <svg viewBox="0 0 220 160" width="100%" style={{ maxWidth: 280 }}>
      {/* Glow filter */}
      <defs>
        <filter id="gauge-glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <filter id="shadow">
          <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor={glowColor} />
        </filter>
      </defs>
      {/* Background track */}
      <path
        d={arcPath(startAngle, startAngle + totalArc, r)}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth="14"
        strokeLinecap="round"
      />
      {/* Tick marks */}
      {[0, 25, 50, 75, 100].map((v) => {
        const ang = startAngle + (v / 100) * totalArc;
        const inner = polar(ang, r - 10);
        const outer = polar(ang, r + 4);
        return (
          <line key={v}
            x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y}
            stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />
        );
      })}
      {/* Fill arc */}
      {score > 0 && (
        <path
          d={arcPath(startAngle, fillAngle, r)}
          fill="none"
          stroke={trackColor}
          strokeWidth="14"
          strokeLinecap="round"
          filter="url(#shadow)"
        />
      )}
      {/* Center score */}
      <text x={cx} y={cy + 8} textAnchor="middle"
        fill="white" fontSize="30" fontWeight="800" fontFamily="Poppins, sans-serif">
        {score}
      </text>
      <text x={cx} y={cy + 26} textAnchor="middle"
        fill="rgba(255,255,255,0.4)" fontSize="10" fontFamily="Inter, sans-serif">
        out of 100
      </text>
      {/* Grade pill */}
      <rect x={cx - 14} y={cy + 36} width="28" height="18" rx="9"
        fill={trackColor} opacity="0.15" />
      <text x={cx} y={cy + 49} textAnchor="middle"
        fill={trackColor} fontSize="11" fontWeight="700" fontFamily="Poppins, sans-serif">
        {grade}
      </text>
    </svg>
  );
};

// ---------------------------------------------------------------------------
// Module card — shows per-module sub-penalty from health score
// ---------------------------------------------------------------------------
const ModuleCard = ({ icon: Icon, title, penalty, weight, tab, jobId, color, description }) => {
  const navigate = useNavigate();
  const weightedPenalty = penalty * weight;
  const barPct = Math.min(100, penalty);

  return (
    <div
      onClick={() => jobId && navigate(`/job/${jobId}`)}
      className={`glass-panel glass-panel-hover rounded-xl p-4 border border-slate-800/80 flex flex-col gap-3 cursor-pointer group`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center`}>
            <Icon className={`w-4 h-4`} style={{ color }} />
          </div>
          <span className="text-sm font-semibold text-slate-200">{title}</span>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 transition-colors" />
      </div>

      {penalty !== null ? (
        <>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Penalty</span>
              <span className="font-medium" style={{ color: penalty > 60 ? '#F87171' : penalty > 30 ? '#FBBF24' : '#4ADE80' }}>
                {penalty.toFixed(1)}/100 (−{weightedPenalty.toFixed(1)}pts)
              </span>
            </div>
            <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${barPct}%`,
                  background: penalty > 60 ? '#F87171' : penalty > 30 ? '#FBBF24' : '#4ADE80',
                }}
              />
            </div>
          </div>
          <p className="text-[11px] text-slate-500">{description}</p>
        </>
      ) : (
        <p className="text-xs text-slate-600 italic">Not yet analyzed</p>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------
const StatusBadge = ({ status }) => {
  const cfg = {
    COMPLETED: { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', dot: 'bg-emerald-400' },
    PROCESSING: { color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20', dot: 'bg-rose-400 animate-pulse' },
    PENDING: { color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', dot: 'bg-amber-400' },
    FAILED: { color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20', dot: 'bg-red-400' },
  };
  const s = cfg[status] || cfg.PENDING;
  return (
    <span className={`flex items-center gap-1.5 text-[10px] font-semibold px-2 py-1 rounded-full border ${s.bg} ${s.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {status}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Health score pill
// ---------------------------------------------------------------------------
const ScorePill = ({ score, grade }) => {
  const color =
    grade === 'A' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' :
      grade === 'B' ? 'text-rose-400 bg-rose-500/10 border-rose-500/20' :
        grade === 'C' ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' :
          grade === 'D' ? 'text-orange-400 bg-orange-500/10 border-orange-500/20' :
            'text-red-400 bg-red-500/10 border-red-500/20';
  return (
    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${color}`}>
      {score} / {grade}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------
const Dashboard = () => {
  const [recentJobs, setRecentJobs] = useState([]);
  const [demoJobs, setDemoJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userData, setUserData] = useState(null);
  const navigate = useNavigate();
  const isDemoMode = localStorage.getItem('is_demo_mode') === 'true';
  const username = isDemoMode ? 'Demo Visitor' : (localStorage.getItem('username') || 'Auditor');

  // Latest completed job for the hero panel
  const latestCompleted = recentJobs.find(j => j.status === 'COMPLETED' && j.results?.health_score);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const token = localStorage.getItem('access_token');
    const isDemoMode = localStorage.getItem('is_demo_mode') === 'true';

    if (!token && !isDemoMode) { navigate('/login'); return; }

    try {
      // Unconditionally fetch demo jobs so they're accessible to everyone
      const demoResp = await fetch('/api/demo-audits/');
      if (demoResp.ok) {
        const dJobs = await demoResp.json();
        setDemoJobs(dJobs);
      }

      if (isDemoMode) {
        setUserData({ username: 'Demo Visitor', email: 'demo@modeldoctor.local' });
        // Under demo mode, recentJobs are simply the pre-computed demo audits
        const demoResp2 = await fetch('/api/demo-audits/');
        if (demoResp2.ok) {
          const jobs = await demoResp2.json();
          setRecentJobs(jobs);
        }
      } else {
        const [healthResp, auditsResp] = await Promise.all([
          fetch('/api/health-check/', { headers: { Authorization: `Bearer ${token}` } }),
          fetch('/api/audits/', { headers: { Authorization: `Bearer ${token}` } }),
        ]);

        if (healthResp.status === 401) { handleLogout(); return; }
        if (healthResp.ok) {
          const d = await healthResp.json();
          setUserData(d.user);
        }

        if (auditsResp.ok) {
          const jobs = await auditsResp.json();
          setRecentJobs(Array.isArray(jobs) ? jobs : (jobs.results || []));
        }
      }
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('username');
    localStorage.removeItem('is_demo_mode');
    navigate('/login');
  };

  const downloadReport = async (jobId, format = 'pdf') => {
    const isDemo = String(jobId).startsWith('demo-');
    const token = localStorage.getItem('access_token');
    const headers = {};
    if (!isDemo && token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const resp = await fetch(`/api/audits/${jobId}/report/?filetype=${format}`, { headers });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        alert(errData.error || 'Failed to download report.');
        return;
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = format === 'pdf' ? 'pdf' : format === 'docx' ? 'docx' : 'html';
      a.download = `modeldoctor_report_${jobId.slice(0, 8)}.${ext}`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Unable to connect to the server to download report.');
    }
  };

  // Derive aggregate stats from recent jobs
  const completedJobs = recentJobs.filter(j => j.status === 'COMPLETED');
  const avgScore = completedJobs.length
    ? Math.round(completedJobs.reduce((acc, j) => acc + (j.results?.health_score?.score || 0), 0) / completedJobs.length)
    : null;
  const totalJobs = recentJobs.length;
  const failedJobs = recentJobs.filter(j => j.status === 'FAILED').length;

  // Hero health score data
  const heroHealth = latestCompleted?.results?.health_score;
  const heroComponents = heroHealth?.components || {};

  const moduleConfigs = [
    {
      key: 'leakage',
      icon: Zap,
      title: 'Target Leakage',
      color: '#F87171',
      description: 'Detects features that contain future or target information at train time.',
      weight: 0.30,
    },
    {
      key: 'calibration',
      icon: Activity,
      title: 'Calibration',
      color: '#F472B6',
      description: 'Brier score: measures if predicted probabilities match observed frequencies.',
      weight: 0.15,
    },
    {
      key: 'overfitting',
      icon: TrendingUp,
      title: 'Overfitting',
      color: '#FBBF24',
      description: 'Train vs validation performance gap across learning curve data points.',
      weight: 0.20,
    },
    {
      key: 'data_quality',
      icon: Database,
      title: 'Data Quality',
      color: '#C084FC',
      description: 'Composite of missing values, duplicates, and outlier rates.',
      weight: 0.15,
    },
    {
      key: 'fairness',
      icon: Shield,
      title: 'Fairness',
      color: '#4ADE80',
      description: 'Phase 5 — disparate impact and demographic parity analysis.',
      weight: 0.20,
    },
  ];

  return (
    <div className="min-h-screen bg-[#1A1220] text-slate-100 flex flex-col font-sans">
      {/* Background ambient glows */}
      <div className="fixed top-0 left-0 w-[600px] h-[600px] bg-pink-900/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="fixed bottom-0 right-0 w-[400px] h-[400px] bg-violet-900/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Navbar */}
      <header className="border-b border-[#3D2F42] bg-[#1F1522]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center shadow-lg shadow-rose-500/5">
            <ShieldAlert className="w-5 h-5 text-rose-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-wide text-white font-display">
              Model<span className="text-rose-400">Doctor</span>
            </h1>
            <p className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold">Audit Dashboard</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col items-end text-sm">
            <span className="text-slate-200 font-medium">{username}</span>
            <span className={`text-xs flex items-center gap-1 ${isDemoMode ? 'text-violet-400' : 'text-emerald-400'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isDemoMode ? 'bg-violet-400' : 'bg-emerald-400 glow-active'}`} />
              {isDemoMode ? 'Demo Sandbox' : 'Secure Session'}
            </span>
          </div>
          {isDemoMode ? (
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-xs bg-violet-600 hover:bg-violet-500 text-white px-3.5 py-2 rounded-lg transition-all font-semibold shadow shadow-violet-650/20"
            >
              <Cpu className="w-3.5 h-3.5" /> Sign In for Live Audits
            </button>
          ) : (
            <button
              id="new-audit-btn"
              onClick={() => navigate('/upload')}
              className="flex items-center gap-2 text-xs bg-rose-600 hover:bg-rose-500 text-white px-3.5 py-2 rounded-lg transition-all font-semibold shadow shadow-rose-600/20"
            >
              <Plus className="w-3.5 h-3.5" /> New Audit
            </button>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs border border-slate-800 hover:border-red-500/30 hover:bg-red-500/5 hover:text-red-400 px-3.5 py-2 rounded-lg transition-all text-slate-400 font-medium"
          >
            <LogOut className="w-3.5 h-3.5" /> Exit
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {isDemoMode && (
          <div className="p-4 rounded-xl bg-violet-900/10 border border-violet-500/20 text-xs text-violet-300 flex items-start gap-3">
            <Info className="w-5 h-5 text-violet-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white block mb-0.5">Demo Sandbox Mode Active</span>
              You are exploring ModelDoctor's capabilities with pre-computed diagnostic audits (Target Leakage, Calibration, and Gender Bias).
              To perform a live audit with your own model file and evaluation dataset, click the <strong>Sign In for Live Audits</strong> button in the header.
            </div>
          </div>
        )}

        {/* ── Aggregate Stats Row ── */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {
              label: 'Total Audits', value: loading ? '—' : totalJobs,
              icon: Cpu, color: 'text-rose-400', sub: 'all time'
            },
            {
              label: 'Completed', value: loading ? '—' : completedJobs.length,
              icon: CheckCircle, color: 'text-emerald-400', sub: 'successful runs'
            },
            {
              label: 'Avg Health Score', value: loading ? '—' : (avgScore !== null ? avgScore : 'N/A'),
              icon: Activity, color: 'text-violet-400', sub: 'across completed jobs'
            },
            {
              label: 'Failed', value: loading ? '—' : failedJobs,
              icon: AlertCircle, color: 'text-red-400', sub: 'errored jobs'
            },
          ].map(({ label, value, icon: Icon, color, sub }) => (
            <div key={label} className="glass-panel glass-panel-hover rounded-xl p-5 border border-slate-800/80">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
              <div className="text-2xl font-bold text-white">{value}</div>
              <p className="text-[10px] text-slate-600 mt-1">{sub}</p>
            </div>
          ))}
        </section>

        {/* ── Hero: Health Score + Module Cards ── */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Gauge Panel */}
          <div className="glass-panel rounded-xl p-6 border border-slate-800/80 flex flex-col items-center gap-4">
            <div className="w-full">
              <h2 className="text-sm font-semibold text-slate-300 mb-0.5">Latest Audit Health Score</h2>
              <p className="text-[11px] text-slate-500">
                {latestCompleted
                  ? `Job ${latestCompleted.id.slice(0, 8)}… · ${new Date(latestCompleted.created_at).toLocaleDateString()}`
                  : 'No completed audits yet'}
              </p>
            </div>

            {loading ? (
              <RefreshCw className="w-8 h-8 animate-spin text-rose-500 my-8" />
            ) : heroHealth ? (
              <>
                <GaugeChart score={heroHealth.score} grade={heroHealth.grade} />
                <div className="w-full space-y-1.5">
                  {Object.entries(heroComponents).map(([key, comp]) => (
                    <div key={key} className="flex items-center gap-2 text-[11px]">
                      <span className="w-20 text-slate-500 capitalize shrink-0">{key.replace('_', ' ')}</span>
                      <div className="flex-1 bg-slate-900 rounded-full h-1 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-rose-500/60"
                          style={{ width: `${comp.penalty || 0}%` }}
                        />
                      </div>
                      <span className="text-slate-500 w-10 text-right">
                        {(comp.penalty || 0).toFixed(0)}
                      </span>
                    </div>
                  ))}
                </div>
                {latestCompleted && (
                  <div className="flex gap-2 w-full">
                    <button
                      onClick={() => downloadReport(latestCompleted.id, 'pdf')}
                      className="flex-1 flex items-center justify-center gap-2 text-xs bg-[#1F1522] hover:bg-[#2A1F30] border border-[#3D2F42] hover:border-rose-500/30 text-slate-300 px-3 py-2 rounded-lg transition-all font-medium"
                    >
                      <Download className="w-3.5 h-3.5 text-rose-400" />
                      PDF Report
                    </button>
                    <button
                      onClick={() => downloadReport(latestCompleted.id, 'docx')}
                      className="flex-1 flex items-center justify-center gap-2 text-xs bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 hover:border-rose-500/60 text-rose-400 px-3 py-2 rounded-lg transition-all font-medium"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Word Doc
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="flex flex-col items-center gap-3 py-8 text-center">
                <BarChart2 className="w-10 h-10 text-slate-700" />
                <p className="text-sm text-slate-600">
                  Upload and run your first audit to see the health score
                </p>
                <button
                  onClick={() => navigate('/upload')}
                  className="text-xs bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 px-4 py-2 rounded-lg border border-rose-500/20 transition-all"
                >
                  Start First Audit →
                </button>
              </div>
            )}
          </div>

          {/* Module Drill-Down Cards */}
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3 content-start">
            <div className="sm:col-span-2">
              <h2 className="text-sm font-semibold text-slate-300 mb-1">Module Risk Breakdown</h2>
              <p className="text-[11px] text-slate-500 mb-3">
                {latestCompleted
                  ? 'Showing sub-penalties for latest completed audit — click any card to drill in.'
                  : 'Run an audit to see per-module risk scores.'}
              </p>
            </div>
            {moduleConfigs.map((mod) => {
              const comp = heroComponents[mod.key];
              return (
                <ModuleCard
                  key={mod.key}
                  icon={mod.icon}
                  title={mod.title}
                  color={mod.color}
                  description={mod.description}
                  weight={mod.weight}
                  penalty={comp ? comp.penalty : null}
                  jobId={latestCompleted?.id}
                  tab={mod.key}
                />
              );
            })}
          </div>
        </section>

        {/* ── Recent Audits List ── */}
        <section className="glass-panel rounded-xl border border-slate-800/80 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Recent Audits</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">Your submitted audit jobs, most recent first</p>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16 gap-3 text-slate-500">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span className="text-sm">Loading audits…</span>
            </div>
          ) : recentJobs.length === 0 ? (
            <div className="flex flex-col items-center gap-4 py-16 text-center">
              <FileText className="w-10 h-10 text-slate-700" />
              <div>
                <p className="text-sm text-slate-500">No audits submitted yet</p>
                <p className="text-xs text-slate-600 mt-1">Upload a model and dataset to run your first audit</p>
              </div>
              <button
                onClick={() => navigate('/upload')}
                className="text-xs bg-rose-600 hover:bg-rose-500 text-white px-4 py-2 rounded-lg transition-all font-semibold"
              >
                Run First Audit
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {recentJobs.slice(0, 10).map((job) => {
                const hs = job.results?.health_score;
                const dateStr = new Date(job.created_at).toLocaleString('en-US', {
                  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                });
                return (
                  <div key={job.id} className="flex flex-col sm:flex-row sm:items-center gap-3 px-6 py-4 hover:bg-slate-900/30 transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <code className="text-xs text-slate-400 font-mono">{job.id.slice(0, 8)}…</code>
                        <StatusBadge status={job.status} />
                        {hs && <ScorePill score={hs.score} grade={hs.grade} />}
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-600">
                        <span>Target: <span className="text-slate-400">{job.target_column}</span></span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />{dateStr}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {job.status === 'COMPLETED' && (
                        <div className="flex gap-1.5">
                          <button
                            onClick={() => downloadReport(job.id, 'pdf')}
                            title="Download PDF Report"
                            className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-rose-400 border border-[#3D2F42] hover:border-rose-500/30 px-2.5 py-1.5 rounded-lg transition-all"
                          >
                            <Download className="w-3 h-3" /> PDF
                          </button>
                          <button
                            onClick={() => downloadReport(job.id, 'docx')}
                            title="Download Word Report"
                            className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-rose-400 border border-[#3D2F42] hover:border-rose-500/30 px-2.5 py-1.5 rounded-lg transition-all"
                          >
                            <Download className="w-3 h-3" /> Word
                          </button>
                        </div>
                      )}
                      <button
                        onClick={() => navigate(`/job/${job.id}`)}
                        className="flex items-center gap-1.5 text-[11px] bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 px-3 py-1.5 rounded-lg transition-all font-medium"
                      >
                        View <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── Explore Pre-computed Model Audits Section ── */}
        {!isDemoMode && demoJobs.length > 0 && (
          <section className="glass-panel rounded-xl border border-slate-800/80 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800/80">
              <h2 className="text-sm font-semibold text-slate-200">Explore Pre-computed Model Audits</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">Explore diagnostics, SHAP features, calibration curves, and fairness audits on pre-run models</p>
            </div>

            <div className="divide-y divide-slate-800/60">
              {demoJobs.map((job) => {
                const hs = job.results?.health_score;
                let title = "";
                let desc = "";
                if (job.id === "demo-titanic-leakage") {
                  title = "Titanic Survivability Model (Target Leakage Demo)";
                  desc = "Demonstrates how target-dependent features artificially inflate accuracy and collapse during validation.";
                } else if (job.id === "demo-calibrated-classifier") {
                  title = "Well-Calibrated Classifier (Model Calibration Demo)";
                  desc = "A standard, healthy model with ideal probability alignment and zero overfitting.";
                } else if (job.id === "demo-biased-credit") {
                  title = "Credit Approval Model (Algorithmic Bias & Drift Demo)";
                  desc = "Analyzes systemic bias against female applicants and tests production dataset shift diagnostics.";
                }

                return (
                  <div key={job.id} className="flex flex-col sm:flex-row sm:items-center gap-3 px-6 py-4 hover:bg-slate-900/30 transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold text-rose-400 font-sans">{title}</span>
                        {hs && <ScorePill score={hs.score} grade={hs.grade} />}
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{desc}</p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-600">
                        <span>Target Column: <span className="text-slate-500 font-mono">{job.target_column}</span></span>
                        {job.protected_attribute && (
                          <span>Protected Attribute: <span className="text-slate-500 font-mono">{job.protected_attribute}</span></span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => navigate(`/job/${job.id}`)}
                        className="flex items-center gap-1 text-[11px] bg-rose-600/10 hover:bg-rose-600/20 border border-rose-500/20 hover:border-rose-500/40 text-rose-400 px-3 py-1.5 rounded-lg transition-all font-semibold"
                      >
                        Inspect Results <ChevronRight className="w-3 h-3" />
                      </button>
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => downloadReport(job.id, 'pdf')}
                          title="Download PDF Report"
                          className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-rose-400 border border-slate-800 hover:border-rose-500/30 px-2.5 py-1.5 rounded-lg transition-all"
                        >
                          <Download className="w-3 h-3" /> PDF
                        </button>
                        <button
                          onClick={() => downloadReport(job.id, 'docx')}
                          title="Download Word Report"
                          className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-rose-400 border border-slate-800 hover:border-rose-500/30 px-2.5 py-1.5 rounded-lg transition-all"
                        >
                          <Download className="w-3 h-3" /> Word
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-[#3D2F42] bg-[#1F1522]/30 py-5 px-8">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between text-xs text-slate-600 gap-2">
          <p>© 2026 ModelDoctor — ML Audit Platform</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1"><Database className="w-3 h-3" /> PostgreSQL</span>
            <span className="flex items-center gap-1"><Zap className="w-3 h-3" /> Celery</span>
            <span className="flex items-center gap-1"><Shield className="w-3 h-3" /> JWT Auth</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;