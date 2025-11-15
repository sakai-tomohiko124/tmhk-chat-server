// Main App JavaScript - TMHKchat メインアプリケーション用スクリプト

(function() {
  'use strict';

  // Tab Navigation
  class TabManager {
    constructor(tabsSelector, panesSelector) {
      this.tabs = document.querySelectorAll(tabsSelector);
      this.panes = document.querySelectorAll(panesSelector);
      this.init();
    }

    init() {
      this.tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => this.switchTab(index));
      });
    }

    switchTab(index) {
      // Remove active class from all tabs and panes
      this.tabs.forEach(tab => tab.classList.remove('active'));
      this.panes.forEach(pane => pane.classList.remove('active'));

      // Add active class to selected tab and pane
      this.tabs[index].classList.add('active');
      this.panes[index].classList.add('active');

      // Save current tab to localStorage
      localStorage.setItem('activeTab', index);
    }

    restoreTab() {
      const savedTab = localStorage.getItem('activeTab');
      if (savedTab !== null) {
        this.switchTab(parseInt(savedTab, 10));
      }
    }
  }

  // Modal Manager
  class ModalManager {
    constructor() {
      this.modals = new Map();
      this.init();
    }

    init() {
      // Find all modals and their triggers
      document.querySelectorAll('[data-modal]').forEach(trigger => {
        const modalId = trigger.getAttribute('data-modal');
        const modal = document.getElementById(modalId);
        
        if (modal) {
          this.modals.set(modalId, modal);
          
          // Open modal on trigger click
          trigger.addEventListener('click', (e) => {
            e.preventDefault();
            this.open(modalId);
          });

          // Close modal on close button click
          const closeBtn = modal.querySelector('.modal-close');
          if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close(modalId));
          }

          // Close modal on overlay click
          modal.addEventListener('click', (e) => {
            if (e.target === modal) {
              this.close(modalId);
            }
          });
        }
      });

      // Close modal on Escape key
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeAll();
        }
      });
    }

    open(modalId) {
      const modal = this.modals.get(modalId);
      if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
      }
    }

    close(modalId) {
      const modal = this.modals.get(modalId);
      if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
      }
    }

    closeAll() {
      this.modals.forEach(modal => {
        modal.classList.remove('show');
      });
      document.body.style.overflow = '';
    }
  }

  // Toast Notification
  class Toast {
    constructor() {
      this.container = this.createContainer();
    }

    createContainer() {
      let container = document.getElementById('toast-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
          position: fixed;
          bottom: 20px;
          right: 20px;
          z-index: 9999;
          display: flex;
          flex-direction: column;
          gap: 10px;
        `;
        document.body.appendChild(container);
      }
      return container;
    }

    show(message, type = 'info', duration = 3000) {
      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.style.cssText = `
        padding: 15px 20px;
        background: ${this.getColor(type)};
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        animation: slideInRight 0.3s ease-out;
        display: flex;
        justify-content: space-between;
        align-items: center;
        min-width: 300px;
        max-width: 500px;
      `;

      const messageSpan = document.createElement('span');
      messageSpan.textContent = message;
      toast.appendChild(messageSpan);

      const closeBtn = document.createElement('button');
      closeBtn.innerHTML = '×';
      closeBtn.style.cssText = `
        background: transparent;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        margin-left: 15px;
        padding: 0;
      `;
      closeBtn.addEventListener('click', () => this.remove(toast));
      toast.appendChild(closeBtn);

      this.container.appendChild(toast);

      if (duration > 0) {
        setTimeout(() => this.remove(toast), duration);
      }

      return toast;
    }

    getColor(type) {
      const colors = {
        success: 'linear-gradient(135deg, #2ecc71, #27ae60)',
        error: 'linear-gradient(135deg, #e74c3c, #c0392b)',
        warning: 'linear-gradient(135deg, #f39c12, #e67e22)',
        info: 'linear-gradient(135deg, #3498db, #2980b9)'
      };
      return colors[type] || colors.info;
    }

    remove(toast) {
      toast.style.animation = 'slideOutRight 0.3s ease-in';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }
  }

  // Form Validator
  class FormValidator {
    constructor(formSelector) {
      this.form = document.querySelector(formSelector);
      if (this.form) {
        this.init();
      }
    }

    init() {
      this.form.addEventListener('submit', (e) => {
        if (!this.validate()) {
          e.preventDefault();
        }
      });

      // Real-time validation
      this.form.querySelectorAll('input, textarea, select').forEach(field => {
        field.addEventListener('blur', () => this.validateField(field));
      });
    }

    validate() {
      let isValid = true;
      const fields = this.form.querySelectorAll('[required]');

      fields.forEach(field => {
        if (!this.validateField(field)) {
          isValid = false;
        }
      });

      return isValid;
    }

    validateField(field) {
      const value = field.value.trim();
      let isValid = true;
      let message = '';

      // Required validation
      if (field.hasAttribute('required') && !value) {
        isValid = false;
        message = 'この項目は必須です';
      }

      // Email validation
      if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
          isValid = false;
          message = '有効なメールアドレスを入力してください';
        }
      }

      // Min length validation
      if (field.hasAttribute('minlength')) {
        const minLength = parseInt(field.getAttribute('minlength'), 10);
        if (value.length < minLength) {
          isValid = false;
          message = `最低${minLength}文字必要です`;
        }
      }

      // Max length validation
      if (field.hasAttribute('maxlength')) {
        const maxLength = parseInt(field.getAttribute('maxlength'), 10);
        if (value.length > maxLength) {
          isValid = false;
          message = `最大${maxLength}文字までです`;
        }
      }

      this.showValidationMessage(field, isValid, message);
      return isValid;
    }

    showValidationMessage(field, isValid, message) {
      // Remove existing error
      const existingError = field.parentNode.querySelector('.error-message');
      if (existingError) {
        existingError.remove();
      }

      if (!isValid && message) {
        field.classList.add('is-invalid');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = `
          color: #e74c3c;
          font-size: 14px;
          margin-top: 5px;
        `;
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
      } else {
        field.classList.remove('is-invalid');
      }
    }
  }

  // LocalStorage Manager
  class StorageManager {
    static set(key, value) {
      try {
        const serialized = JSON.stringify(value);
        localStorage.setItem(key, serialized);
        return true;
      } catch (error) {
        console.error('Failed to save to localStorage:', error);
        return false;
      }
    }

    static get(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      } catch (error) {
        console.error('Failed to read from localStorage:', error);
        return defaultValue;
      }
    }

    static remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch (error) {
        console.error('Failed to remove from localStorage:', error);
        return false;
      }
    }

    static clear() {
      try {
        localStorage.clear();
        return true;
      } catch (error) {
        console.error('Failed to clear localStorage:', error);
        return false;
      }
    }
  }

  // Utility Functions
  const Utils = {
    debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    throttle(func, limit) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },

    formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
      const d = new Date(date);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');
      const seconds = String(d.getSeconds()).padStart(2, '0');

      return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
    },

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    copyToClipboard(text) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text);
      } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        return Promise.resolve();
      }
    }
  };

  // Initialize on DOM ready
  function init() {
    // Initialize Tab Manager if tabs exist
    const tabs = document.querySelectorAll('.nav-tab');
    const panes = document.querySelectorAll('.tab-pane');
    if (tabs.length > 0 && panes.length > 0) {
      const tabManager = new TabManager('.nav-tab', '.tab-pane');
      tabManager.restoreTab();
    }

    // Initialize Modal Manager
    const modalManager = new ModalManager();

    // Initialize Toast globally
    window.toast = new Toast();

    // Initialize Form Validators
    document.querySelectorAll('form[data-validate]').forEach(form => {
      new FormValidator(`#${form.id}`);
    });

    // Add animation styles to head
    addAnimationStyles();
  }

  function addAnimationStyles() {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideInRight {
        from {
          opacity: 0;
          transform: translateX(100%);
        }
        to {
          opacity: 1;
          transform: translateX(0);
        }
      }

      @keyframes slideOutRight {
        from {
          opacity: 1;
          transform: translateX(0);
        }
        to {
          opacity: 0;
          transform: translateX(100%);
        }
      }
    `;
    document.head.appendChild(style);
  }

  // Export to global scope
  window.TMHKChat = {
    TabManager,
    ModalManager,
    Toast,
    FormValidator,
    StorageManager,
    Utils
  };

  // Auto-initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
