// Achievement Component - アチーブメント管理コンポーネント (Vanilla JS)

(function() {
  'use strict';

  class Achievement {
    constructor(containerId, options = {}) {
      this.container = document.getElementById(containerId);
      if (!this.container) {
        console.error(`Container with id "${containerId}" not found`);
        return;
      }

      this.options = {
        autoSave: true,
        storageKey: 'user_achievements',
        showNotifications: true,
        ...options
      };

      this.state = {
        achievements: [],
        unlockedAchievements: new Set(),
        totalPoints: 0
      };

      this.init();
    }

    init() {
      // Load saved achievements from localStorage
      this.loadAchievements();

      // Define default achievements
      this.defineDefaultAchievements();

      // Render initial UI
      this.render();

      // Setup event listeners
      this.setupEventListeners();
    }

    defineDefaultAchievements() {
      const defaultAchievements = [
        {
          id: 'first_message',
          title: '初めてのメッセージ',
          description: '初めてのメッセージを送信しました',
          icon: '💬',
          points: 10,
          category: 'basic'
        },
        {
          id: 'ten_messages',
          title: 'おしゃべり好き',
          description: '10件のメッセージを送信しました',
          icon: '📝',
          points: 50,
          category: 'basic'
        },
        {
          id: 'first_friend',
          title: '初めての友達',
          description: '初めて友達を追加しました',
          icon: '👥',
          points: 20,
          category: 'social'
        },
        {
          id: 'five_friends',
          title: '人気者',
          description: '5人の友達を追加しました',
          icon: '🌟',
          points: 100,
          category: 'social'
        },
        {
          id: 'first_group',
          title: 'グループリーダー',
          description: '初めてグループを作成しました',
          icon: '👔',
          points: 30,
          category: 'group'
        },
        {
          id: 'photo_upload',
          title: 'フォトグラファー',
          description: '初めて写真をアップロードしました',
          icon: '📸',
          points: 15,
          category: 'media'
        },
        {
          id: 'video_upload',
          title: 'ビデオクリエイター',
          description: '初めて動画をアップロードしました',
          icon: '🎬',
          points: 25,
          category: 'media'
        },
        {
          id: 'profile_complete',
          title: 'プロフィール完成',
          description: 'プロフィールを完全に入力しました',
          icon: '✅',
          points: 40,
          category: 'profile'
        },
        {
          id: 'night_owl',
          title: '夜更かし',
          description: '深夜0時以降にメッセージを送信しました',
          icon: '🦉',
          points: 5,
          category: 'special'
        },
        {
          id: 'early_bird',
          title: '早起き',
          description: '午前5時前にメッセージを送信しました',
          icon: '🌅',
          points: 5,
          category: 'special'
        },
        {
          id: 'week_streak',
          title: '継続は力なり',
          description: '7日連続でログインしました',
          icon: '🔥',
          points: 75,
          category: 'streak'
        },
        {
          id: 'game_master',
          title: 'ゲームマスター',
          description: 'ミニゲームで初勝利しました',
          icon: '🎮',
          points: 50,
          category: 'game'
        }
      ];

      // Merge with existing achievements (don't overwrite)
      defaultAchievements.forEach(achievement => {
        if (!this.state.achievements.find(a => a.id === achievement.id)) {
          this.state.achievements.push(achievement);
        }
      });

      this.saveAchievements();
    }

    loadAchievements() {
      try {
        const saved = localStorage.getItem(this.options.storageKey);
        if (saved) {
          const data = JSON.parse(saved);
          this.state.unlockedAchievements = new Set(data.unlocked || []);
          this.state.totalPoints = data.totalPoints || 0;
          this.state.achievements = data.achievements || [];
        }
      } catch (error) {
        console.error('Failed to load achievements:', error);
      }
    }

    saveAchievements() {
      if (!this.options.autoSave) return;

      try {
        const data = {
          unlocked: Array.from(this.state.unlockedAchievements),
          totalPoints: this.state.totalPoints,
          achievements: this.state.achievements
        };
        localStorage.setItem(this.options.storageKey, JSON.stringify(data));
      } catch (error) {
        console.error('Failed to save achievements:', error);
      }
    }

    unlock(achievementId) {
      if (this.state.unlockedAchievements.has(achievementId)) {
        return false; // Already unlocked
      }

      const achievement = this.state.achievements.find(a => a.id === achievementId);
      if (!achievement) {
        console.warn(`Achievement "${achievementId}" not found`);
        return false;
      }

      this.state.unlockedAchievements.add(achievementId);
      this.state.totalPoints += achievement.points;
      this.saveAchievements();

      if (this.options.showNotifications) {
        this.showUnlockNotification(achievement);
      }

      this.render();
      return true;
    }

    showUnlockNotification(achievement) {
      // Create notification element
      const notification = document.createElement('div');
      notification.className = 'achievement-notification';
      notification.innerHTML = `
        <div class="achievement-notification-content">
          <div class="achievement-notification-icon">${achievement.icon}</div>
          <div class="achievement-notification-text">
            <div class="achievement-notification-title">アチーブメント解除!</div>
            <div class="achievement-notification-name">${achievement.title}</div>
            <div class="achievement-notification-points">+${achievement.points} ポイント</div>
          </div>
        </div>
      `;

      // Add styles
      notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideInRight 0.5s ease-out, fadeOut 0.5s ease-in 3.5s;
        min-width: 300px;
      `;

      document.body.appendChild(notification);

      // Remove after animation
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 4000);

      // Add notification styles to head if not already present
      if (!document.getElementById('achievement-notification-styles')) {
        const style = document.createElement('style');
        style.id = 'achievement-notification-styles';
        style.textContent = `
          .achievement-notification-content {
            display: flex;
            align-items: center;
            gap: 15px;
          }
          .achievement-notification-icon {
            font-size: 48px;
          }
          .achievement-notification-text {
            flex: 1;
          }
          .achievement-notification-title {
            font-weight: 600;
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 5px;
          }
          .achievement-notification-name {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 5px;
          }
          .achievement-notification-points {
            font-size: 16px;
            font-weight: 600;
            color: #ffd700;
          }
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
          @keyframes fadeOut {
            from {
              opacity: 1;
            }
            to {
              opacity: 0;
            }
          }
        `;
        document.head.appendChild(style);
      }
    }

    render() {
      if (!this.container) return;

      const categories = ['basic', 'social', 'group', 'media', 'profile', 'special', 'streak', 'game'];
      const categoryNames = {
        basic: '基本',
        social: 'ソーシャル',
        group: 'グループ',
        media: 'メディア',
        profile: 'プロフィール',
        special: '特別',
        streak: '継続',
        game: 'ゲーム'
      };

      let html = `
        <div class="achievement-container">
          <div class="achievement-header">
            <h2>アチーブメント</h2>
            <div class="achievement-stats">
              <div class="achievement-stat">
                <span class="stat-value">${this.state.unlockedAchievements.size}</span>
                <span class="stat-label">解除済み</span>
              </div>
              <div class="achievement-stat">
                <span class="stat-value">${this.state.achievements.length}</span>
                <span class="stat-label">全体</span>
              </div>
              <div class="achievement-stat">
                <span class="stat-value">${this.state.totalPoints}</span>
                <span class="stat-label">ポイント</span>
              </div>
            </div>
          </div>
      `;

      categories.forEach(category => {
        const categoryAchievements = this.state.achievements.filter(a => a.category === category);
        if (categoryAchievements.length === 0) return;

        html += `
          <div class="achievement-category">
            <h3 class="category-title">${categoryNames[category]}</h3>
            <div class="achievement-grid">
        `;

        categoryAchievements.forEach(achievement => {
          const isUnlocked = this.state.unlockedAchievements.has(achievement.id);
          html += `
            <div class="achievement-card ${isUnlocked ? 'unlocked' : 'locked'}" data-id="${achievement.id}">
              <div class="achievement-icon">${achievement.icon}</div>
              <div class="achievement-info">
                <div class="achievement-title">${achievement.title}</div>
                <div class="achievement-description">${achievement.description}</div>
                <div class="achievement-points">+${achievement.points} ポイント</div>
              </div>
              ${isUnlocked ? '<div class="achievement-badge">✓</div>' : ''}
            </div>
          `;
        });

        html += `
            </div>
          </div>
        `;
      });

      html += '</div>';

      this.container.innerHTML = html;
      this.addStyles();
    }

    addStyles() {
      if (document.getElementById('achievement-styles')) return;

      const style = document.createElement('style');
      style.id = 'achievement-styles';
      style.textContent = `
        .achievement-container {
          padding: 20px;
        }
        .achievement-header {
          margin-bottom: 30px;
        }
        .achievement-header h2 {
          font-size: 28px;
          margin-bottom: 15px;
        }
        .achievement-stats {
          display: flex;
          gap: 20px;
        }
        .achievement-stat {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 15px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          min-width: 100px;
        }
        .stat-value {
          font-size: 32px;
          font-weight: 700;
          color: #667eea;
        }
        .stat-label {
          font-size: 14px;
          opacity: 0.8;
        }
        .achievement-category {
          margin-bottom: 30px;
        }
        .category-title {
          font-size: 20px;
          margin-bottom: 15px;
          border-bottom: 2px solid rgba(255, 255, 255, 0.2);
          padding-bottom: 10px;
        }
        .achievement-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 15px;
        }
        .achievement-card {
          position: relative;
          padding: 20px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 15px;
          display: flex;
          gap: 15px;
          transition: all 0.3s;
        }
        .achievement-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }
        .achievement-card.locked {
          opacity: 0.5;
        }
        .achievement-card.unlocked {
          background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
          border-color: #667eea;
        }
        .achievement-icon {
          font-size: 48px;
          flex-shrink: 0;
        }
        .achievement-info {
          flex: 1;
        }
        .achievement-title {
          font-size: 18px;
          font-weight: 600;
          margin-bottom: 5px;
        }
        .achievement-description {
          font-size: 14px;
          opacity: 0.8;
          margin-bottom: 8px;
        }
        .achievement-points {
          font-size: 14px;
          font-weight: 600;
          color: #ffd700;
        }
        .achievement-badge {
          position: absolute;
          top: 10px;
          right: 10px;
          width: 30px;
          height: 30px;
          background: #2ecc71;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          color: white;
        }
        @media (max-width: 768px) {
          .achievement-grid {
            grid-template-columns: 1fr;
          }
          .achievement-stats {
            flex-wrap: wrap;
          }
        }
      `;
      document.head.appendChild(style);
    }

    setupEventListeners() {
      // Click on achievement card to view details
      this.container.addEventListener('click', (e) => {
        const card = e.target.closest('.achievement-card');
        if (card) {
          const achievementId = card.dataset.id;
          const achievement = this.state.achievements.find(a => a.id === achievementId);
          if (achievement) {
            this.showAchievementDetail(achievement);
          }
        }
      });
    }

    showAchievementDetail(achievement) {
      const isUnlocked = this.state.unlockedAchievements.has(achievement.id);
      
      if (window.toast) {
        window.toast.show(
          `${achievement.icon} ${achievement.title}\n${achievement.description}\n${isUnlocked ? '解除済み' : '未解除'} - ${achievement.points}ポイント`,
          isUnlocked ? 'success' : 'info',
          5000
        );
      }
    }

    // Public API methods
    getProgress() {
      return {
        total: this.state.achievements.length,
        unlocked: this.state.unlockedAchievements.size,
        percentage: Math.round((this.state.unlockedAchievements.size / this.state.achievements.length) * 100),
        points: this.state.totalPoints
      };
    }

    isUnlocked(achievementId) {
      return this.state.unlockedAchievements.has(achievementId);
    }

    reset() {
      this.state.unlockedAchievements.clear();
      this.state.totalPoints = 0;
      this.saveAchievements();
      this.render();
    }
  }

  // Export to global scope
  window.Achievement = Achievement;

  // Auto-initialize if container exists
  document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('achievement-container');
    if (container) {
      window.achievementManager = new Achievement('achievement-container');
    }
  });
})();
