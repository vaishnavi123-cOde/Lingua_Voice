/**
 * SPACE STARS - ULTRA PERFORMANCE OPTIMIZED
 * Generates thousands of animated stars with smooth parallax
 */

class StarsGenerator {
  constructor() {
    this.starsContainer = document.querySelector('.stars');
    if (!this.starsContainer) return;
    
    this.stars = [];
    this.generateStars();
    this.setupParallax();
  }

  generateStars() {
    const starCount = 300; // 300 stars for visible coverage
    const window_width = window.innerWidth;
    const window_height = window.innerHeight * 2; // Cover visible + scroll area

    for (let i = 0; i < starCount; i++) {
      const star = document.createElement('div');
      star.className = `star s${Math.floor(Math.random() * 4) + 1}`;
      
      const x = Math.random() * window_width;
      const y = Math.random() * window_height;
      const delay = Math.random() * 6;

      star.style.left = x + 'px';
      star.style.top = y + 'px';
      star.style.animationDelay = delay + 's';

      this.starsContainer.appendChild(star);
      this.stars.push({ element: star, x, y, delay });
    }
  }

  setupParallax() {
    let ticking = false;
    
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const scrollY = window.scrollY * 0.1;
          this.starsContainer.style.transform = `translateY(${scrollY}px)`;
          ticking = false;
        });
        ticking = true;
      }
    });

    // Mouse parallax
    document.addEventListener('mousemove', (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 20;
      const y = (e.clientY / window.innerHeight - 0.5) * 20;
      this.starsContainer.style.transform = `translate(${x}px, ${y}px)`;
    });
  }
}

/**
 * SMOOTH SCROLL ENHANCEMENT
 * Optimized scrolling with momentum
 */
class SmoothScroll {
  static init() {
    // Smooth scroll to sections on anchor click
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', (e) => {
        const href = anchor.getAttribute('href');
        if (href === '#') return;

        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
          });
        }
      });
    });

    // Optimize scroll performance
    this.optimizeScrollPerformance();
  }

  static optimizeScrollPerformance() {
    let ticking = false;
    let lastScrollY = 0;

    window.addEventListener('scroll', () => {
      lastScrollY = window.scrollY;

      if (!ticking) {
        requestAnimationFrame(() => {
          // Update any scroll-dependent elements here
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }
}

/**
 * TOAST NOTIFICATIONS - LIGHTWEIGHT
 */
class Toast {
  static show(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: rgba(10, 14, 31, 0.95);
      border: 2px solid;
      border-radius: 8px;
      padding: 1rem 1.5rem;
      color: white;
      z-index: 2000;
      font-weight: 600;
      animation: slide-up 0.3s ease-out;
      max-width: 90%;
      word-wrap: break-word;
    `;

    const colors = {
      success: '#00ff88',
      error: '#ff0080',
      warning: '#ffaa00',
      info: '#00d4ff'
    };

    toast.style.borderColor = colors[type] || colors.info;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'fade-in 0.3s ease-out reverse forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  static success(msg) { this.show(msg, 'success'); }
  static error(msg) { this.show(msg, 'error'); }
  static warning(msg) { this.show(msg, 'warning'); }
  static info(msg) { this.show(msg, 'info'); }
}

/**
 * MODAL SYSTEM - MINIMAL
 */
class Modal {
  static open(selector) {
    const modal = document.querySelector(selector);
    if (!modal) return;
    modal.classList.add('active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  static close(selector) {
    const modal = document.querySelector(selector);
    if (!modal) return;
    modal.classList.remove('active');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  static setupCloseButtons() {
    document.querySelectorAll('.modal-close').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const modal = e.target.closest('.modal');
        if (modal) this.close(`.${modal.className}`);
      });
    });

    // Close on ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(m => {
          Modal.close(`.${m.className}`);
        });
      }
    });
  }
}

/**
 * FORM VALIDATOR - SIMPLE
 */
class FormValidator {
  static validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  static validatePassword(password) {
    return password.length >= 8;
  }

  static validateForm(formSelector) {
    const form = document.querySelector(formSelector);
    if (!form) return true;

    let isValid = true;

    form.querySelectorAll('input[type="email"]').forEach(input => {
      if (!this.validateEmail(input.value)) {
        input.style.borderColor = '#ff0080';
        isValid = false;
      }
    });

    form.querySelectorAll('input[type="password"]').forEach(input => {
      if (!this.validatePassword(input.value)) {
        input.style.borderColor = '#ff0080';
        isValid = false;
      }
    });

    return isValid;
  }
}

/**
 * THEME TOGGLE - PERSISTENT
 */
class ThemeSwitcher {
  static init() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);

    toggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);

      toggle.style.transform = 'rotate(180deg)';
      setTimeout(() => {
        toggle.style.transform = 'rotate(0)';
      }, 600);
    });
  }
}

/**
 * ANIMATION OBSERVER - STAGGERED ANIMATIONS
 */
class AnimationObserver {
  static init() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          entry.target.style.animation = `slide-up 0.6s ease-out ${i * 0.1}s forwards`;
          entry.target.style.opacity = '0';
        }
      });
    }, { threshold: 0.1 });

    // Observe elements with animation classes
    document.querySelectorAll('.slide-up, .fade-in').forEach(el => {
      observer.observe(el);
    });
  }
}

/**
 * PERFORMANCE MONITORING
 */
class PerformanceMonitor {
  static init() {
    if (window.performance && window.performance.timing) {
      window.addEventListener('load', () => {
        setTimeout(() => {
          const timing = window.performance.timing;
          const loadTime = timing.loadEventEnd - timing.navigationStart;
          console.log(`Page load time: ${loadTime}ms`);
        }, 0);
      });
    }
  }
}

/**
 * INITIALIZE ALL SYSTEMS
 */
function initSpace() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
}

function start() {
  // Core systems
  new StarsGenerator();
  SmoothScroll.init();
  ThemeSwitcher.init();
  Modal.setupCloseButtons();
  
  // Enhancements
  AnimationObserver.init();
  PerformanceMonitor.init();

  // Expose to window
  window.SpaceUI = { Toast, Modal, FormValidator, SmoothScroll };

  console.log('Space UI initialized - Ready to launch!');
}

initSpace();
