document.addEventListener('DOMContentLoaded', () => {
  if (window.__TINCHLIK_CHAT_INIT__) {
    return;
  }
  window.__TINCHLIK_CHAT_INIT__ = true;

  const chatRoot = document.getElementById('chatRoot');
  const currentUserId = Number(chatRoot?.dataset.currentUserId || 0);
  if (!Number.isFinite(currentUserId) || currentUserId <= 0) {
    console.warn('[chat] current user id missing; chat ownership cannot be resolved safely.');
  }

  const composer = document.getElementById('chatComposer');
  const input = document.getElementById('chatMessageInput');
  const sendButton = document.getElementById('chatSendButton');
  const messagesContainer = document.getElementById('chat-messages');
  const onlineCountEl = document.getElementById('online-count');
  const emptyChatEl = document.getElementById('empty-chat');
  const typingIndicator = document.getElementById('typing-indicator');
  const imageButton = document.getElementById('image-button');
  const audioButton = document.getElementById('audio-button');
  const imageInput = document.getElementById('image-input');
  const audioInput = document.getElementById('audio-input');
  const errorBox = document.getElementById('chatError');

  if (!composer || !input || !sendButton || !messagesContainer) {
    console.warn('[chat] required chat elements missing; chat disabled.');
    return;
  }

  const state = {
    socket: null,
    isSending: false,
    typingTimer: null,
    latestMessageId: null,
    isNearBottom: true,
    activeMenuId: null,
  };

  const sendUrl = composer.dataset.sendUrl || '/chat/send/';

  function showToast(message) {
    let toast = document.getElementById('chat-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'chat-toast';
      toast.className = 'chat-toast';
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('show'), 1800);
  }

  function closeActiveMenu() {
    if (!state.activeMenuId) return;
    const menu = document.querySelector(`.message-menu[data-message-id="${state.activeMenuId}"]`);
    if (menu) {
      menu.classList.add('hidden');
    }
    const button = document.querySelector(`.message-menu-button[data-message-id="${state.activeMenuId}"]`);
    if (button) {
      button.setAttribute('aria-expanded', 'false');
      button.classList.remove('is-open');
    }
    state.activeMenuId = null;
  }

  function setError(message) {
    if (!errorBox) return;
    if (!message) {
      errorBox.hidden = true;
      errorBox.textContent = '';
      return;
    }
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function setSendState(isLoading) {
    state.isSending = isLoading;
    sendButton.disabled = isLoading;
    sendButton.setAttribute('aria-busy', String(isLoading));
    sendButton.innerHTML = isLoading ? '<span>Yuborilmoqda...</span>' : '<span>Yuborish</span>';
  }

  function escapeHtml(value = '') {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMessageTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function updateScrollState() {
    state.isNearBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight < 120;
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function renderMessage(message) {
    if (!message || message.is_deleted) return;

    const messageId = Number(message.id);
    if (messageId && document.querySelector(`[data-message-id="${messageId}"]`)) {
      return;
    }

    const senderId = Number(message.sender_id);
    const isOwn = Number.isFinite(senderId) && Number.isFinite(currentUserId) && currentUserId > 0 && senderId === currentUserId;

    const wrapper = document.createElement('article');
    wrapper.className = `message ${isOwn ? 'own' : 'other'}`;
    wrapper.dataset.messageId = message.id;

    const row = document.createElement('div');
    row.className = `message-row ${isOwn ? 'own' : 'other'}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    if (message.sender_avatar) {
      avatar.innerHTML = `<img src="${message.sender_avatar}" alt="${escapeHtml(message.sender_name || 'User')}" />`;
    } else {
      const initials = (message.sender_name || 'U').split(' ').slice(0, 2).map((word) => word[0]).join('').toUpperCase();
      avatar.textContent = initials || 'U';
    }

    const bubbleWrap = document.createElement('div');
    bubbleWrap.className = `message-bubble-wrap ${isOwn ? 'own' : 'other'}`;

    const card = document.createElement('div');
    card.className = 'message-card';

    const header = document.createElement('div');
    header.className = 'message-header';

    const senderName = document.createElement('span');
    senderName.className = 'sender-name';
    senderName.textContent = message.sender_name || 'User';

    const time = document.createElement('span');
    time.className = 'message-time';
    time.textContent = formatMessageTime(message.created_at);

    header.appendChild(senderName);
    header.appendChild(time);
    card.appendChild(header);

    if (message.reply_to) {
      const replyBox = document.createElement('div');
      replyBox.className = 'reply-box';
      replyBox.innerHTML = `<strong>${escapeHtml(message.reply_to.sender_name || 'User')}</strong><span>${escapeHtml(message.reply_to.text || '')}</span>`;
      card.appendChild(replyBox);
    }

    const text = document.createElement('div');
    text.className = 'message-text';
    text.textContent = message.text || '';
    card.appendChild(text);

    if (message.message_type === 'image' && (message.image_url || message.image)) {
      const imageWrap = document.createElement('div');
      imageWrap.className = 'message-image';
      imageWrap.innerHTML = `<img src="${message.image_url || message.image}" alt="Chat image" />`;
      card.appendChild(imageWrap);
    }

    if (message.message_type === 'audio' && (message.audio_url || message.audio)) {
      const audioWrap = document.createElement('div');
      audioWrap.className = 'message-audio';
      audioWrap.innerHTML = `<audio class="audio-player" controls src="${message.audio_url || message.audio}"></audio>`;
      card.appendChild(audioWrap);
    }

    const actions = document.createElement('div');
    actions.className = 'message-actions';

    const menuButton = document.createElement('button');
    menuButton.type = 'button';
    menuButton.className = 'message-menu-button';
    menuButton.setAttribute('aria-label', 'Xabar amallari');
    menuButton.dataset.messageId = String(message.id);
    menuButton.textContent = '⋯';

    const menu = document.createElement('div');
    menu.className = 'message-menu hidden';
    menu.dataset.messageId = String(message.id);
    menu.setAttribute('role', 'menu');

    const copyAction = document.createElement('button');
    copyAction.type = 'button';
    copyAction.className = 'message-menu-item';
    copyAction.textContent = 'Nusxa olish';
    copyAction.addEventListener('click', async () => {
      try {
        const textToCopy = message.text || '';
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(textToCopy);
        } else {
          const temp = document.createElement('textarea');
          temp.value = textToCopy;
          document.body.appendChild(temp);
          temp.select();
          document.execCommand('copy');
          temp.remove();
        }
        showToast('Xabar nusxalandi');
      } catch (error) {
        console.error('[chat] copy failed', error);
        showToast('Nusxa olish ishlamadi');
      }
      closeActiveMenu();
    });

    menu.appendChild(copyAction);

    if (isOwn && message.can_delete !== false) {
      const deleteAction = document.createElement('button');
      deleteAction.type = 'button';
      deleteAction.className = 'message-menu-item danger';
      deleteAction.textContent = 'O‘chirish';
      deleteAction.addEventListener('click', () => {
        const confirmed = window.confirm('Xabarni o\'chirmoqchimisiz?');
        if (!confirmed) {
          closeActiveMenu();
          return;
        }
        deleteMessage(message.id, wrapper);
        closeActiveMenu();
      });
      menu.appendChild(deleteAction);
    }

    menuButton.addEventListener('click', (event) => {
      event.stopPropagation();
      const open = state.activeMenuId === String(message.id);
      closeActiveMenu();
      if (open) return;
      menu.classList.remove('hidden');
      menuButton.classList.add('is-open');
      menuButton.setAttribute('aria-expanded', 'true');
      state.activeMenuId = String(message.id);
    });

    if (isOwn) {
      actions.appendChild(menuButton);
    }

    bubbleWrap.appendChild(card);
    bubbleWrap.appendChild(menu);
    bubbleWrap.appendChild(actions);
    row.appendChild(isOwn ? bubbleWrap : avatar);
    row.appendChild(isOwn ? avatar : bubbleWrap);
    wrapper.appendChild(row);
    messagesContainer.appendChild(wrapper);

    document.addEventListener('click', (event) => {
      if (!event.target.closest('.message-menu-button') && !event.target.closest('.message-menu')) {
        closeActiveMenu();
      }
    }, { once: true });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeActiveMenu();
      }
    }, { once: true });

    if (message.id && (!state.latestMessageId || message.id > state.latestMessageId)) {
      state.latestMessageId = message.id;
    }

    if (emptyChatEl) emptyChatEl.classList.add('hidden');
  }

  function updateTypingIndicator(username, isTyping) {
    if (!typingIndicator) return;

    const current = typingIndicator.dataset.typingUsers || '';
    const users = current ? current.split('|').filter(Boolean) : [];

    if (isTyping) {
      if (!users.includes(username)) users.push(username);
    } else {
      const filtered = users.filter((value) => value !== username);
      typingIndicator.dataset.typingUsers = filtered.join('|');
    }

    const activeUsers = typingIndicator.dataset.typingUsers ? typingIndicator.dataset.typingUsers.split('|').filter(Boolean) : [];

    if (activeUsers.length) {
      typingIndicator.textContent = `${activeUsers.join(', ')} yozmoqda...`;
      typingIndicator.classList.remove('hidden');
    } else {
      typingIndicator.textContent = '';
      typingIndicator.classList.add('hidden');
    }
  }

  function sendTypingEvent(isTyping) {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
    state.socket.send(JSON.stringify({ type: 'typing', is_typing: isTyping }));
  }

  function handleSocketMessage(event) {
    const data = JSON.parse(event.data);

    if (data.type === 'presence' && onlineCountEl) {
      onlineCountEl.textContent = `${data.online_count} online`;
      return;
    }

    if (data.type === 'new_message') {
      renderMessage(data.message);
      if (state.isNearBottom) scrollToBottom();
      return;
    }

    if (data.type === 'typing') {
      updateTypingIndicator(data.username, data.is_typing);
      return;
    }

    if (data.type === 'delete_message') {
      const messageNode = document.querySelector(`[data-message-id="${data.message_id}"]`);
      if (messageNode) {
        messageNode.classList.add('removing');
        setTimeout(() => messageNode.remove(), 180);
      }
      return;
    }

    if (data.type === 'error') {
      console.error('[chat]', data.message || 'Unknown chat error');
      setError(data.message || 'Xabar yuborilmadi. Qayta urinib ko‘ring.');
    }
  }

  function prepareSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${window.location.host}/ws/chat/`;
    state.socket = new WebSocket(url);
    state.socket.addEventListener('message', handleSocketMessage);
    state.socket.addEventListener('open', () => {
      fetchHistory();
      setSendState(false);
      setError('');
    });
    state.socket.addEventListener('error', (event) => {
      console.error('[chat] websocket error', event);
      setError('Chat serverga ulanib bo‘lmadi. Qayta urinib ko‘ring.');
      setSendState(false);
    });
    state.socket.addEventListener('close', () => {
      setSendState(false);
      setTimeout(prepareSocket, 1500);
    });
  }

  async function fetchHistory() {
    try {
      const response = await fetch('/chat/history/?page=1', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });

      if (!response.ok) throw new Error('History failed');

      const result = await response.json();
      const messages = result.messages || [];

      if (!messages.length && emptyChatEl) {
        emptyChatEl.classList.remove('hidden');
      } else if (messages.length) {
        messagesContainer.innerHTML = '';
        messages.forEach((message) => renderMessage(message));
        scrollToBottom();
      }

      // Ownership is derived from the authenticated user ID on the page, not from stale browser-local guesses.
    } catch (error) {
      console.error('[chat] history fetch failed', error);
    }
  }

  async function sendMessage() {
    if (state.isSending) return;

    const messageText = input.value.trim();
    if (!messageText) {
      input.focus();
      return;
    }

    setSendState(true);
    setError('');

    try {
      const response = await fetch(sendUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1] || '',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ message: messageText }),
      });

      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.error || 'Xabar yuborilmadi.');
      }

      input.value = '';
      input.style.height = 'auto';
      sendTypingEvent(false);

      if (result.message) {
        renderMessage(result.message);
      }

      if (state.isNearBottom) {
        scrollToBottom();
      }
    } catch (error) {
      console.error('[chat] send failed', error);
      setError(error.message || 'Xabar yuborilmadi. Qayta urinib ko‘ring.');
    } finally {
      setSendState(false);
    }
  }

  async function deleteMessage(messageId, messageElement) {
    try {
      const response = await fetch(`/chat/delete/${messageId}/`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1] || '',
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.error || 'Delete failed');
      }

      if (messageElement) {
        messageElement.classList.add('removing');
        setTimeout(() => messageElement.remove(), 180);
      }
      showToast('Xabar o\'chirildi');
    } catch (error) {
      console.error('[chat] delete failed', error);
      setError(error.message || 'Xabarni o\'chirish mumkin emas.');
    }
  }

  function handleTextInput() {
    const hasText = input.value.trim().length > 0;

    if (hasText) {
      sendTypingEvent(true);
      clearTimeout(state.typingTimer);
      state.typingTimer = setTimeout(() => sendTypingEvent(false), 1200);
    } else {
      sendTypingEvent(false);
    }

    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
  }

  sendButton.addEventListener('click', sendMessage);

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  input.addEventListener('input', handleTextInput);

  if (imageButton && imageInput) {
    imageButton.addEventListener('click', () => imageInput.click());
  }

  if (audioButton && audioInput) {
    audioButton.addEventListener('click', () => audioInput.click());
  }

  if (imageInput) {
    imageInput.addEventListener('change', async () => {
      const file = imageInput.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('image', file);
      if (input.value.trim()) formData.append('text', input.value.trim());

      const response = await fetch('/chat/upload/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1],
        },
        body: formData,
      });

      const result = await response.json();
      if (!response.ok) {
        setError(result.error || 'Image upload failed');
        return;
      }

      imageInput.value = '';
      input.value = '';
      sendTypingEvent(false);
      if (result.message) renderMessage(result.message);
    });
  }

  if (audioInput) {
    audioInput.addEventListener('change', async () => {
      const file = audioInput.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('audio', file);
      if (input.value.trim()) formData.append('text', input.value.trim());

      const response = await fetch('/chat/upload/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1],
        },
        body: formData,
      });

      const result = await response.json();
      if (!response.ok) {
        setError(result.error || 'Audio upload failed');
        return;
      }

      audioInput.value = '';
      input.value = '';
      sendTypingEvent(false);
      if (result.message) renderMessage(result.message);
    });
  }

  messagesContainer.addEventListener('scroll', updateScrollState);
  setSendState(false);
  setError('');
  prepareSocket();
});
