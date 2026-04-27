/**
 * KontentPyper -- Signup Page Logic
 * Calls POST /api/v1/auth/register, then auto-logs in and redirects.
 */

(function () {
  'use strict';

  var form = document.getElementById('signupForm');
  var btn = document.getElementById('submitBtn');
  var alertBox = document.getElementById('alert');

  function showAlert(msg, type) {
    alertBox.className = 'alert show ' + type;
    alertBox.querySelector('.alert-msg').textContent = msg;
  }

  function hideAlert() {
    alertBox.className = 'alert';
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    hideAlert();

    var username = document.getElementById('username').value.trim();
    var email = document.getElementById('email').value.trim();
    var password = document.getElementById('password').value;
    var confirm = document.getElementById('confirmPassword').value;

    // Client-side validation
    if (!username || !email || !password || !confirm) {
      showAlert('All fields are required.', 'error');
      return;
    }

    if (password.length < 8) {
      showAlert('Password must be at least 8 characters.', 'error');
      return;
    }

    if (password !== confirm) {
      showAlert('Passwords do not match.', 'error');
      return;
    }

    btn.classList.add('loading');
    btn.disabled = true;

    try {
      // Step 1: Register
      var regRes = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, email: email, password: password })
      });

      if (!regRes.ok) {
        var regErr = await regRes.json();
        throw new Error(regErr.detail || 'Registration failed.');
      }

      // Step 2: Auto-login
      var loginBody = new URLSearchParams();
      loginBody.append('username', email);
      loginBody.append('password', password);

      var loginRes = await fetch('/api/v1/auth/login', {
        method: 'POST',
        credentials: 'include',
        body: loginBody
      });

      if (!loginRes.ok) {
        // Registration succeeded but login failed -- just redirect to login
        showAlert('Account created! Redirecting to login...', 'success');
        setTimeout(function () { window.location.href = '/dashboard/login'; }, 1500);
        return;
      }

      var loginData = await loginRes.json();
      localStorage.setItem('kp_token', loginData.access_token);
      localStorage.setItem('token', loginData.access_token);

      showAlert('Account created! Entering dashboard...', 'success');
      setTimeout(function () { window.location.href = '/dashboard'; }, 800);

    } catch (err) {
      showAlert(err.message, 'error');
    } finally {
      btn.classList.remove('loading');
      btn.disabled = false;
    }
  });
})();
