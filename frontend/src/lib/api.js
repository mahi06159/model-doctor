/**
 * api.js — Centralised API base-URL helper
 *
 * In production the Vite build inlines VITE_API_URL (set by render.yaml to the
 * deployed backend's URL, e.g. https://modeldoctor-backend.onrender.com).
 * In local dev VITE_API_URL is undefined, so API_BASE falls back to '' and the
 * existing Vite proxy in vite.config.js transparently forwards /api/* requests.
 */

export const API_BASE = import.meta.env.VITE_API_URL ?? '';

/**
 * Prefix `path` with the backend base URL.
 * `path` must start with a '/'.
 *
 * @param {string} path  e.g. '/api/token/'
 * @returns {string}     e.g. 'https://modeldoctor-backend.onrender.com/api/token/'
 */
export function apiUrl(path) {
  return `${API_BASE}${path}`;
}
