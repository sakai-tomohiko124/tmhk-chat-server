// Chat Socket.IO - チャット用Socket.IO統合スクリプト

(function() {
  'use strict';

  class ChatSocket {
    constructor(options = {}) {
      this.options = {
        autoConnect: true,
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        ...options
      };

      this.socket = null;
      this.isConnected = false;
      this.messageHandlers = new Map();
      this.eventListeners = new Map();
      
      if (this.options.autoConnect) {
        this.connect();
      }
    }

    connect() {
      if (this.socket) {
        console.warn('Socket already connected');
        return;
      }

      // Initialize Socket.IO connection
      this.socket = io({
        reconnection: this.options.reconnection,
        reconnectionAttempts: this.options.reconnectionAttempts,
        reconnectionDelay: this.options.reconnectionDelay
      });

      // Setup default event handlers
      this.setupDefaultHandlers();
    }

    setupDefaultHandlers() {
      // Connection events
      this.socket.on('connect', () => {
        this.isConnected = true;
        console.log('Socket.IO connected');
        this.trigger('connected');
      });

      this.socket.on('disconnect', (reason) => {
        this.isConnected = false;
        console.log('Socket.IO disconnected:', reason);
        this.trigger('disconnected', reason);
      });

      this.socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
        this.trigger('error', error);
      });

      this.socket.on('reconnect', (attemptNumber) => {
        console.log('Reconnected after', attemptNumber, 'attempts');
        this.trigger('reconnected', attemptNumber);
      });

      this.socket.on('reconnect_attempt', (attemptNumber) => {
        console.log('Reconnection attempt', attemptNumber);
        this.trigger('reconnecting', attemptNumber);
      });

      this.socket.on('reconnect_failed', () => {
        console.error('Reconnection failed');
        this.trigger('reconnect_failed');
      });
    }

    // Join a chat room
    joinRoom(roomName, userData = {}) {
      if (!this.isConnected) {
        console.error('Cannot join room: Socket not connected');
        return;
      }

      this.socket.emit('join_room', {
        room: roomName,
        ...userData
      });

      this.trigger('room_joined', { room: roomName, userData });
    }

    // Leave a chat room
    leaveRoom(roomName) {
      if (!this.isConnected) {
        console.error('Cannot leave room: Socket not connected');
        return;
      }

      this.socket.emit('leave_room', {
        room: roomName
      });

      this.trigger('room_left', { room: roomName });
    }

    // Send a message
    sendMessage(message, roomName = null) {
      if (!this.isConnected) {
        console.error('Cannot send message: Socket not connected');
        return;
      }

      const payload = {
        message: message,
        timestamp: new Date().toISOString()
      };

      if (roomName) {
        payload.room = roomName;
      }

      this.socket.emit('send_message', payload);
      this.trigger('message_sent', payload);
    }

    // Send file
    sendFile(file, roomName = null, onProgress = null) {
      if (!this.isConnected) {
        console.error('Cannot send file: Socket not connected');
        return Promise.reject(new Error('Socket not connected'));
      }

      return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = (e) => {
          const payload = {
            file: {
              name: file.name,
              data: e.target.result,
              type: file.type,
              size: file.size
            },
            timestamp: new Date().toISOString()
          };

          if (roomName) {
            payload.room = roomName;
          }

          this.socket.emit('send_message', payload);
          this.trigger('file_sent', payload);
          resolve(payload);
        };

        reader.onerror = (error) => {
          reject(error);
        };

        if (onProgress) {
          reader.onprogress = (e) => {
            if (e.lengthComputable) {
              const percentComplete = (e.loaded / e.total) * 100;
              onProgress(percentComplete);
            }
          };
        }

        reader.readAsDataURL(file);
      });
    }

    // Send typing indicator
    sendTyping(isTyping, roomName = null, username = '') {
      if (!this.isConnected) return;

      this.socket.emit('typing', {
        username: username,
        room: roomName,
        isTyping: isTyping
      });
    }

    // Listen for new messages
    onMessage(handler) {
      this.socket.on('new_message', (data) => {
        handler(data);
        this.trigger('message_received', data);
      });
    }

    // Listen for offline messages
    onOfflineMessages(handler) {
      this.socket.on('receive_offline_messages', (messages) => {
        handler(messages);
        this.trigger('offline_messages_received', messages);
      });
    }

    // Listen for typing indicators
    onTyping(handler) {
      this.socket.on('user_typing', (data) => {
        handler(data);
        this.trigger('user_typing', data);
      });
    }

    // Listen for user list updates
    onUserListUpdate(handler) {
      this.socket.on('update_user_list', (users) => {
        handler(users);
        this.trigger('user_list_updated', users);
      });
    }

    // Listen for file upload results
    onFileUploadResult(handler) {
      this.socket.on('file_upload_result', (result) => {
        handler(result);
        this.trigger('file_upload_result', result);
      });
    }

    // Generic event listener
    on(eventName, handler) {
      if (this.socket) {
        this.socket.on(eventName, handler);
      }

      // Store handler for internal event system
      if (!this.eventListeners.has(eventName)) {
        this.eventListeners.set(eventName, []);
      }
      this.eventListeners.get(eventName).push(handler);
    }

    // Remove event listener
    off(eventName, handler) {
      if (this.socket) {
        this.socket.off(eventName, handler);
      }

      const handlers = this.eventListeners.get(eventName);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    }

    // Trigger internal event
    trigger(eventName, data = null) {
      const handlers = this.eventListeners.get(eventName);
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler(data);
          } catch (error) {
            console.error(`Error in event handler for ${eventName}:`, error);
          }
        });
      }
    }

    // Mark messages as read
    markAsRead(roomName) {
      if (!this.isConnected) return;

      this.socket.emit('mark_as_read', {
        room: roomName
      });
    }

    // Disconnect
    disconnect() {
      if (this.socket) {
        this.socket.disconnect();
        this.socket = null;
        this.isConnected = false;
      }
    }

    // Check connection status
    isSocketConnected() {
      return this.isConnected && this.socket && this.socket.connected;
    }
  }

  // Chat UI Helper
  class ChatUI {
    constructor(containerId) {
      this.container = document.getElementById(containerId);
      this.messageContainer = null;
      this.inputContainer = null;
    }

    // Render a message bubble
    renderMessage(message, isMine = false, safe = true) {
      if (!this.messageContainer) {
        this.messageContainer = this.container.querySelector('.chat-messages') || this.container;
      }

      const messageDiv = document.createElement('div');
      messageDiv.className = `message ${isMine ? 'mine' : 'other'}`;

      const bubble = document.createElement('div');
      bubble.className = `message-bubble${safe ? '' : ' unsafe-message'}`;

      const content = document.createElement('div');
      content.className = 'message-content';

      // Handle different message types
      if (message.message) {
        content.textContent = message.message;
      } else if (message.file_path) {
        content.appendChild(this.renderFile(message));
      }

      bubble.appendChild(content);
      messageDiv.appendChild(bubble);

      // Add message info (username, timestamp)
      const info = document.createElement('div');
      info.className = 'message-info';
      info.innerHTML = `
        <span class="username">${this.escapeHtml(message.username || '')}</span>
        <span class="timestamp">${this.formatTimestamp(message.timestamp)}</span>
      `;
      messageDiv.appendChild(info);

      this.messageContainer.appendChild(messageDiv);
      this.scrollToBottom();

      return messageDiv;
    }

    // Render file attachment
    renderFile(message) {
      const fileType = message.file_type;
      const filePath = message.file_path;

      if (fileType === 'image') {
        const img = document.createElement('img');
        img.src = `/uploads/${filePath}`;
        img.alt = 'Image';
        img.style.maxWidth = '100%';
        img.style.borderRadius = '10px';
        return img;
      } else if (fileType === 'video') {
        const video = document.createElement('video');
        video.src = `/uploads/${filePath}`;
        video.controls = true;
        video.style.maxWidth = '100%';
        video.style.borderRadius = '10px';
        return video;
      } else if (fileType === 'pdf') {
        const link = document.createElement('a');
        link.href = `/uploads/${filePath}`;
        link.target = '_blank';
        link.textContent = `📄 ${filePath}`;
        return link;
      }

      // Default file link
      const link = document.createElement('a');
      link.href = `/uploads/${filePath}`;
      link.target = '_blank';
      link.textContent = `📎 ${filePath}`;
      return link;
    }

    // Scroll chat to bottom
    scrollToBottom() {
      if (this.messageContainer) {
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
      }
    }

    // Show typing indicator
    showTypingIndicator(username) {
      const indicator = document.getElementById('typing-indicator');
      if (indicator) {
        indicator.textContent = `${username} が入力中です...`;
        indicator.style.display = 'block';
      }
    }

    // Hide typing indicator
    hideTypingIndicator() {
      const indicator = document.getElementById('typing-indicator');
      if (indicator) {
        indicator.textContent = '';
        indicator.style.display = 'none';
      }
    }

    // Utility: Escape HTML
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Utility: Format timestamp
    formatTimestamp(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      const now = new Date();
      const isToday = date.toDateString() === now.toDateString();

      if (isToday) {
        return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
      }
      return date.toLocaleString('ja-JP', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  }

  // Export to global scope
  window.ChatSocket = ChatSocket;
  window.ChatUI = ChatUI;
})();
