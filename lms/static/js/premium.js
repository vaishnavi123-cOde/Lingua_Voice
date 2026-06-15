/* =====================================
   PREMIUM UI - JavaScript
   Interactive Hovering Stars Effect
   ===================================== */

class PremiumUI {
  constructor() {
    this.stars = [];
    this.initHoveringStars();
    this.setupEventListeners();
    this.setupNavigation();
    this.setupButtons();
    this.setupMagneticButtons();
  }

  /**
   * Initialize hovering stars that follow mouse
   */
  initHoveringStars() {
    const starsContainer = document.querySelector('.stars-bg');
    if (!starsContainer) return;

    document.addEventListener('mousemove', (e) => {
      this.createHoveringStar(e.clientX, e.clientY, starsContainer);
    });
  }

  /**
   * Create a hovering star at mouse position
   */
  createHoveringStar(x, y, container) {
    const star = document.createElement('div');
    star.className = 'star';
    
    const size = Math.random() * 2 + 1;
    const duration = Math.random() * 0.6 + 0.4;  // 0.4 to 1 second instead of 1.5 to 3
    
    star.style.width = size + 'px';
    star.style.height = size + 'px';
    star.style.left = x + 'px';
    star.style.top = y + 'px';
    star.style.animationDuration = duration + 's';
    star.style.position = 'fixed';
    star.style.pointerEvents = 'none';
    star.style.zIndex = '1';
    
    container.appendChild(star);
    
    // Remove star after animation completes
    setTimeout(() => star.remove(), duration * 1000);
  }

  /**
   * Setup all event listeners
   */
  setupEventListeners() {
    window.addEventListener('scroll', () => this.handleScroll());
    window.addEventListener('resize', () => this.handleResize());
  }

  /**
   * Setup navigation
   */
  setupNavigation() {
    const navLinks = document.querySelectorAll('nav a, nav button');
    navLinks.forEach(link => {
      if (link.href && link.href.includes('#')) {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const target = link.getAttribute('href');
          const element = document.querySelector(target);
          if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
          }
        });
      }
    });
  }

  /**
   * Setup button functionality
   */
  setupButtons() {
    // Login button
    document.querySelectorAll('[data-action="login"]').forEach(btn => {
      btn.addEventListener('click', () => this.navigateTo('/login'));
    });

    // Signup button
    document.querySelectorAll('[data-action="signup"]').forEach(btn => {
      btn.addEventListener('click', () => this.navigateTo('/signup'));
    });

    // Dashboard button
    document.querySelectorAll('[data-action="dashboard"]').forEach(btn => {
      btn.addEventListener('click', () => this.navigateTo('/dashboard'));
    });

    // Logout button
    document.querySelectorAll('[data-action="logout"]').forEach(btn => {
      btn.addEventListener('click', () => this.logout());
    });

    // Smooth scroll links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(anchor.getAttribute('href'));
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
        }
      });
    });
  }

  /**
   * Setup magnetic button effect for main CTAs
   */
  setupMagneticButtons() {
    const magneticBtns = document.querySelectorAll('.btn-xl');
    
    magneticBtns.forEach(btn => {
      // Add smooth transition for snapping back
      btn.style.transition = 'transform 0.3s cubic-bezier(0.25, 1, 0.5, 1), box-shadow 0.3s ease';
      
      btn.addEventListener('mousemove', (e) => {
        const rect = btn.getBoundingClientRect();
        const h = rect.width / 2;
        const v = rect.height / 2;
        const x = e.clientX - rect.left - h;
        const y = e.clientY - rect.top - v;
        
        // Move button slightly towards the cursor
        btn.style.transform = `translate(${x * 0.3}px, ${y * 0.3}px) scale(1.05)`;
      });
      
      btn.addEventListener('mouseleave', () => {
        // Snap back to original position
        btn.style.transform = 'translate(0px, 0px) scale(1)';
      });
    });
  }

  /**
   * Navigate to URL
   */
  navigateTo(path) {
    window.location.href = path;
  }

  /**
   * Logout functionality
   */
  logout() {
    if (confirm('Are you sure you want to log out?')) {
      window.location.href = '/logout';
    }
  }

  /**
   * Handle scroll events
   */
  handleScroll() {
    const nav = document.querySelector('nav');
    if (!nav) return;
    if (window.scrollY > 50) {
      nav.style.background = 'rgba(10, 13, 20, 0.95)';
    } else {
      nav.style.background = 'rgba(10, 13, 20, 0.9)';
    }
  }

  /**
   * Handle window resize
   */
  handleResize() {
    // Handle responsive adjustments
  }

  /**
   * Show toast notification
   */
  static toast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: ${type === 'error' ? '#ff4444' : '#44ff44'};
      color: white;
      padding: 1rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      z-index: 1000;
      animation: slide-up 0.3s ease-out;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }
}

class ScrollVideoSequence {
  constructor() {
    this.container = document.getElementById('videoScrollContainer');
    if (!this.container) return;

    this.frames = [
      document.getElementById('seqFrame1'),
      document.getElementById('seqFrame2'),
      document.getElementById('seqFrame3')
    ];
    
    this.heroSection = document.getElementById('hero');
    this.featuresSection = document.getElementById('features');

    window.addEventListener('scroll', () => requestAnimationFrame(() => this.handleScroll()), { passive: true });
    this.handleScroll(); // init
  }

  handleScroll() {
    const rect = this.container.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    
    // total scrolling room before container leaves screen
    const scrollableDistance = rect.height - windowHeight;
    const scrolled = -rect.top;
    
    if (scrolled < 0 || scrolled > rect.height) {
        // We are outside bounds but keep ends pinned visually handled by sticky layout
    }

    let progress = scrolled / scrollableDistance;
    progress = Math.max(0, Math.min(1, progress));

    // Smooth frame crossfades simulating video scrubbing
    this.frames[0].style.opacity = progress <= 0.3 ? 1 : Math.max(0, 1 - ((progress - 0.3) / 0.1));
    
    if (progress >= 0.25 && progress <= 0.75) {
      if (progress < 0.35) this.frames[1].style.opacity = (progress - 0.25) / 0.1;
      else if (progress > 0.65) this.frames[1].style.opacity = Math.max(0, 1 - ((progress - 0.65) / 0.1));
      else this.frames[1].style.opacity = 1;
    } else {
      this.frames[1].style.opacity = 0;
    }

    if (progress >= 0.6) {
      if (progress < 0.7) this.frames[2].style.opacity = (progress - 0.6) / 0.1;
      else this.frames[2].style.opacity = 1;
    } else {
      this.frames[2].style.opacity = 0;
    }

    // Continuous Buttery Smooth Camera Transform (Apple Style)
    // Scale from 1.25 down to 0.85 as we scroll
    const currentScale = 1.25 - (progress * 0.4);
    // Translate slightly down
    const currentTranslateY = progress * 10;
    
    if (!this.imgStack) this.imgStack = document.querySelector('.bg-image-stack');
    if (this.imgStack) {
      this.imgStack.style.transform = `scale(${currentScale}) translateY(${currentTranslateY}%)`;
    }

    // Parallax text scrolling
    if (progress < 0.3) {
      let heroAlpha = Math.max(0, 1 - (progress / 0.25));
      this.heroSection.style.opacity = heroAlpha;
      this.heroSection.style.transform = `translateY(calc(-50% + ${progress * -100}px))`;
      this.heroSection.style.pointerEvents = heroAlpha > 0.5 ? 'auto' : 'none';
      this.heroSection.classList.add('active');
    } else {
      this.heroSection.style.opacity = 0;
      this.heroSection.style.pointerEvents = 'none';
      this.heroSection.classList.remove('active');
    }

    // Frame 2 tagline: visible alongside the close-up eagle (progress 0.25 → 0.65)
    if (!this.frame2Section) this.frame2Section = document.getElementById('frame2-tagline');
    if (this.frame2Section) {
      if (progress >= 0.25 && progress <= 0.65) {
        let f2Alpha;
        if (progress < 0.35) f2Alpha = (progress - 0.25) / 0.1;
        else if (progress > 0.55) f2Alpha = Math.max(0, 1 - ((progress - 0.55) / 0.1));
        else f2Alpha = 1;
        this.frame2Section.style.opacity = f2Alpha;
        this.frame2Section.style.transform = `translateY(-50%)`;
        this.frame2Section.style.pointerEvents = f2Alpha > 0.5 ? 'auto' : 'none';
      } else {
        this.frame2Section.style.opacity = 0;
        this.frame2Section.style.pointerEvents = 'none';
      }
    }

    if (progress > 0.65) {
      let featureAlpha = Math.min(1, (progress - 0.65) / 0.2);
      this.featuresSection.style.opacity = featureAlpha;
      this.featuresSection.style.transform = `translateY(calc(-50% + ${(1 - featureAlpha) * 60}px))`;
      this.featuresSection.style.pointerEvents = featureAlpha > 0.5 ? 'auto' : 'none';
      this.featuresSection.classList.add('active');
    } else {
      this.featuresSection.style.opacity = 0;
      this.featuresSection.style.pointerEvents = 'none';
      this.featuresSection.classList.remove('active');
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.premiumUI = new PremiumUI();
  window.scrollSeq = new ScrollVideoSequence();
  console.log('Premium UI with Hovering Stars & Video Scroll initialized successfully');
});
