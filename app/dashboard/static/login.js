/**
 * KontentPyper — Login Page Script
 * Handles form submission, JWT storage, and auth redirect.
 */

const API_BASE = '/api/v1';

// Redirect if already authenticated
if (localStorage.getItem('kp_token')) {
  window.location.replace('/dashboard');
}

document.addEventListener('DOMContentLoaded', () => {
  const form    = document.getElementById('loginForm');
  const alert   = document.getElementById('alert');
  const btn     = document.getElementById('submitBtn');

  function showAlert(msg, type) {
    alert.className = `alert ${type} show`;
    alert.querySelector('.alert-msg').textContent = msg;
  }

  function setLoading(on) {
    btn.classList.toggle('loading', on);
    btn.disabled = on;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    alert.className = 'alert';
    setLoading(true);

    const identifier = document.getElementById('identifier').value.trim();
    const password   = document.getElementById('password').value;

    try {
      const body = new URLSearchParams({ username: identifier, password });
      const res  = await fetch(`${API_BASE}/auth/login`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body:    body.toString(),
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem('kp_token', data.access_token);
        showAlert('Authenticated. Entering...', 'success');
        setTimeout(() => window.location.replace('/dashboard'), 700);
      } else {
        showAlert(data.detail || 'Authentication failed.', 'error');
        setLoading(false);
      }
    } catch {
      showAlert('Network error — is the server running?', 'error');
      setLoading(false);
    }
  });
});
