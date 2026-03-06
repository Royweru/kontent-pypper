/**
 * KontentPyper -- Landing Page Logic
 * Auth-aware CTAs, scroll animations, mobile nav toggle
 */

(function () {
  'use strict';

  // ── Auth-aware CTAs ───────────────────────────────────────
  const token = localStorage.getItem('token');
  if (token) {
    // User is logged in -- show "Open Dashboard" instead of "Create Account"
    const primary = document.getElementById('heroCtaPrimary');
    const secondary = document.getElementById('heroCtaSecondary');
    const navLogin = document.getElementById('navLogin');
    const navCta = document.getElementById('navCta');

    if (primary) primary.style.display = 'none';
    if (secondary) secondary.style.display = 'inline-flex';
    if (navLogin) navLogin.style.display = 'none';
    if (navCta) { navCta.href = '/dashboard'; navCta.textContent = 'Dashboard'; }
  }

  // ── Navbar scroll effect ──────────────────────────────────
  const nav = document.getElementById('pubNav');
  window.addEventListener('scroll', function () {
    if (window.scrollY > 40) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
  }, { passive: true });

  // ── Mobile nav toggle ─────────────────────────────────────
  const toggle = document.getElementById('navToggle');
  const links = document.getElementById('navLinks');

  toggle.addEventListener('click', function () {
    links.classList.toggle('open');
    toggle.innerHTML = links.classList.contains('open') ? '&#10005;' : '&#9776;';
  });

  // Close mobile nav when clicking a link
  links.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () {
      links.classList.remove('open');
      toggle.innerHTML = '&#9776;';
    });
  });

  // ── Scroll animations (IntersectionObserver) ──────────────
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll('.feature-card, .step-item').forEach(function (el) {
    observer.observe(el);
  });

  // ── Smooth scroll for anchor links ────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
})();
