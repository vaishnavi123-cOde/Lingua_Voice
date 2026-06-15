/* ===========================
   UI UTILITIES & INTERACTIONS
   Enhanced User Experience
   =========================== */

class Toast {
  static show(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.classList.add('toast-hide');
      setTimeout(() => toast.remove(), 400);
    }, duration);
  }

  static success(message, duration = 3000) {
    this.show(message, 'success', duration);
  }

  static error(message, duration = 4000) {
    this.show(message, 'error', duration);
  }

  static warning(message, duration = 3500) {
    this.show(message, 'warning', duration);
  }

  static info(message, duration = 3000) {
    this.show(message, 'info', duration);
  }
}

class Modal {
  static open(content, title = '') {
    let modal = document.getElementById('modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'modal';
      modal.className = 'modal';
      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h2 id="modal-title"></h2>
            <button class="modal-close" onclick="Modal.close()">×</button>
          </div>
          <div id="modal-body"></div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    modal.classList.add('active');
  }

  static close() {
    const modal = document.getElementById('modal');
    if (modal) {
      modal.classList.remove('active');
    }
  }
}

class Dropdown {
  static init() {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
      const trigger = dropdown.querySelector('.dropdown-trigger');
      const menu = dropdown.querySelector('.dropdown-menu');

      if (trigger && menu) {
        trigger.addEventListener('click', (e) => {
          e.stopPropagation();
          menu.classList.toggle('active');
        });
      }
    });

    document.addEventListener('click', () => {
      document.querySelectorAll('.dropdown-menu').forEach(menu => {
        menu.classList.remove('active');
      });
    });
  }
}

class Tabs {
  static init() {
    document.querySelectorAll('.tabs').forEach(tabsContainer => {
      const buttons = tabsContainer.querySelectorAll('.tab-button');
      const contents = tabsContainer.parentElement.querySelectorAll('.tab-content');

      buttons.forEach((button, index) => {
        button.addEventListener('click', () => {
          buttons.forEach(b => b.classList.remove('active'));
          contents.forEach(c => c.classList.remove('active'));

          button.classList.add('active');
          contents[index].classList.add('active');
        });
      });

      // Set first tab as active
      if (buttons.length > 0) {
        buttons[0].classList.add('active');
        contents[0].classList.add('active');
      }
    });
  }
}

class Animations {
  static stagger(selector, delay = 100) {
    const elements = document.querySelectorAll(selector);
    elements.forEach((el, index) => {
      el.style.animationDelay = `${index * delay}ms`;
    });
  }

  static fadeIn(element, duration = 600) {
    element.style.animation = `fadeIn ${duration}ms`;
  }

  static slideUp(element, duration = 600) {
    element.style.animation = `slideUp ${duration}ms`;
  }

  static slideDown(element, duration = 600) {
    element.style.animation = `slideDown ${duration}ms`;
  }

  static pulse(element, duration = 2000) {
    element.style.animation = `pulse ${duration}ms infinite`;
  }
}

class Loading {
  static show(message = 'Loading...') {
    let loader = document.getElementById('loader');
    if (!loader) {
      loader = document.createElement('div');
      loader.id = 'loader';
      loader.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        backdrop-filter: blur(4px);
      `;
      document.body.appendChild(loader);
    }

    loader.innerHTML = `
      <div style="text-align: center; color: white;">
        <div style="font-size: 2rem; animation: spin 1s linear infinite; margin-bottom: 1rem;">⌛</div>
        <p>${message}</p>
      </div>
    `;
    loader.style.display = 'flex';
  }

  static hide() {
    const loader = document.getElementById('loader');
    if (loader) {
      loader.style.display = 'none';
    }
  }
}

class ScrollReveal {
  static init() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.animation = 'slideInUp 0.6s ease forwards';
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.reveal').forEach(el => {
      observer.observe(el);
    });
  }
}

class Form {
  static validate(formElement) {
    if (!formElement) return true;

    const inputs = formElement.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;

    inputs.forEach(input => {
      if (!input.value.trim()) {
        input.style.borderColor = '#ef4444';
        isValid = false;
      } else {
        input.style.borderColor = '';
      }
    });

    return isValid;
  }

  static onChange(input) {
    if (input.value.trim()) {
      input.style.borderColor = '';
    }
  }
}

class Storage {
  static set(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  static get(key) {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
  }

  static remove(key) {
    localStorage.removeItem(key);
  }

  static clear() {
    localStorage.clear();
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  Dropdown.init();
  Tabs.init();
  ScrollReveal.init();

  // Close modal on outside click
  document.addEventListener('click', (e) => {
    const modal = document.getElementById('modal');
    if (modal && e.target === modal) {
      Modal.close();
    }
  });

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) {
      document.querySelectorAll('.dropdown-menu').forEach(menu => {
        menu.classList.remove('active');
      });
    }
  });
});

// Expose to window for global access
window.Toast = Toast;
window.Modal = Modal;
window.Animations = Animations;
window.Loading = Loading;
window.Form = Form;
window.Storage = Storage;
