/**
 * KontentPyper — Login Page Script
 * Handles form submission, JWT storage, and auth redirect.
 */

const API_BASE = '/api/v1';

// Redirect if already authenticated
(async function redirectIfAuthenticated() {
  if (localStorage.getItem('kp_token')) {
    window.location.replace('/dashboard');
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
    if (res.ok) window.location.replace('/dashboard');
  } catch {}
})();

document.addEventListener('DOMContentLoaded', () => {
  const form    = document.getElementById('loginForm');
  const alert   = document.getElementById('alert');
  const btn     = document.getElementById('submitBtn');
  const googleBtn = document.getElementById('googleLoginBtn');

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
        credentials: 'include',
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

  if (googleBtn) {
    googleBtn.addEventListener('click', async () => {
      alert.className = 'alert';
      googleBtn.disabled = true;

      try {
        const res = await fetch(`${API_BASE}/auth/google/initiate`, {
          credentials: 'include',
        });
        const data = await res.json();

        if (!res.ok || !data.auth_url) {
          showAlert(data.detail || 'Google login is not configured.', 'error');
          googleBtn.disabled = false;
          return;
        }

        window.location.href = data.auth_url;
      } catch {
        showAlert('Network error -- is the server running?', 'error');
        googleBtn.disabled = false;
      }
    });
  }
});
