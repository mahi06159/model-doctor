import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import JobStatus from './pages/JobStatus';
import ProtectedRoute from './components/ProtectedRoute';

/**
 * Main App Component
 * Configures client-side routing using React Router.
 * Protects primary audit routes.
 */
function App() {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected Routes */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/upload" 
          element={
            <ProtectedRoute>
              <Upload />
            </ProtectedRoute>
          } 
        />

        <Route 
          path="/job/:id" 
          element={
            <ProtectedRoute>
              <JobStatus />
            </ProtectedRoute>
          } 
        />

        {/* Catch-all fallback, redirecting back to main index */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
