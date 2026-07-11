import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, User, AlertCircle } from 'lucide-react';
import { apiUrl } from '../lib/api';

/**
 * Login Page Component
 * Renders a glassmorphic login card with dark theme design.
 * Integrates with /api/token/ Django endpoint.
 */
const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // If already logged in, redirect straight to dashboard
  useEffect(() => {
    if (localStorage.getItem('access_token')) {
      navigate('/');
    }
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(apiUrl('/api/token/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('username', username);
        navigate('/');
      } else {
        setError(data.detail || 'Invalid username or password. Make sure a superuser is created.');
      }
    } catch (err) {
      setError('Unable to connect to the backend server. Verify docker-compose services are running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#1A1220] px-4 relative overflow-hidden">
      {/* Decorative gradient glowing spheres */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-pink-900/20 rounded-full blur-[100px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-900/20 rounded-full blur-[100px] pointer-events-none"></div>

      <div className="w-full max-w-md glass-panel rounded-2xl p-8 shadow-2xl relative z-10 border border-[#3D2F42]">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mb-4 shadow-lg shadow-rose-500/5">
            <Shield className="w-8 h-8 text-rose-400" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white font-display">
            Model<span className="text-rose-400">Doctor</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">Machine Learning Model Auditing Platform</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-3 text-red-200 text-sm">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Username
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <User className="w-4 h-4 text-slate-500" />
              </div>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-[#1F1522]/60 border border-[#3D2F42] focus:border-rose-500/50 focus:ring-1 focus:ring-rose-500/50 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-slate-500 outline-none transition-all text-sm"
                placeholder="e.g. admin"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                <Lock className="w-4 h-4 text-slate-500" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[#1F1522]/60 border border-[#3D2F42] focus:border-rose-500/50 focus:ring-1 focus:ring-rose-500/50 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-slate-500 outline-none transition-all text-sm"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-gradient-to-r from-rose-500 to-fuchsia-500 hover:from-rose-400 hover:to-fuchsia-400 text-white font-medium rounded-lg py-2.5 shadow-lg shadow-rose-500/10 focus:outline-none focus:ring-2 focus:ring-rose-500/50 disabled:opacity-50 transition-all flex items-center justify-center text-sm"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Authenticating...
              </span>
            ) : (
              'Sign In'
            )}
          </button>
          
          <div className="relative flex py-2 items-center">
            <div className="flex-grow border-t border-[#3D2F42]"></div>
            <span className="flex-shrink mx-3 text-slate-600 text-xs font-semibold uppercase tracking-wider">or</span>
            <div className="flex-grow border-t border-[#3D2F42]"></div>
          </div>

          <button
            type="button"
            onClick={() => {
              localStorage.setItem('is_demo_mode', 'true');
              navigate('/');
            }}
            className="w-full bg-[#1F1522] hover:bg-[#2A1F30] text-violet-400 border border-violet-950 hover:border-violet-500/30 font-medium rounded-lg py-2.5 transition-all flex items-center justify-center text-sm shadow shadow-violet-950/20"
          >
            Explore Demo Sandbox
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-[#3D2F42] text-center">
          <p className="text-xs text-slate-500">
            For local setup, create a user using: <br />
            <code className="bg-[#1F1522] px-1.5 py-0.5 rounded text-rose-400 mt-1 inline-block border border-[#3D2F42]">
              docker compose exec backend python manage.py createsuperuser
            </code>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
