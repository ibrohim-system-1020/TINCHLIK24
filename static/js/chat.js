document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('chatMessageForm');
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

  if (!form || !input || !sendButton || !messagesContainer) {
    console.warn('[chat] required chat elements missing; chat disabled.');
    return;
  }

  const state = {
    socket: null,
    isSending: false,
    typingTimer: null,
    replyToMessageId: null,
    userInfo: null,
    latestMessageId: null,
    isNearBottom: true,
  };

  function setSendState(isLoading) {
    state.isSending = isLoading;
    sendButton.disabled = isLoading;
    sendButton.setAttribute('aria-busy', String(isLoading));
    sendButton.textContent = isLoading ? 'Yuborilmoqda...' : 'Yuborish';
  }

  function escapeHtml(value = '') {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
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

    const wrapper = document.createElement('article');
    wrapper.className = 'message';
    if (message.sender_id === state.userInfo?.id) wrapper.classList.add('own');
    wrapper.dataset.messageId = message.id;

    const row = document.createElement('div');
    row.className = 'message-row';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    if (message.sender_avatar) {
      avatar.innerHTML = `<img src="${message.sender_avatar}" alt="${escapeHtml(message.sender_name || 'User')}" />`;
    } else {
      const initials = (message.sender_name || 'U').split(' ').slice(0, 2).map((word) => word[0]).join('').toUpperCase();
      avatar.textContent = initials || 'U';
    }

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

    row.appendChild(avatar);
    row.appendChild(card);
    wrapper.appendChild(row);
    messagesContainer.appendChild(wrapper);

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
      if (messageNode) messageNode.remove();
      return;
    }

    if (data.type === 'error') {
      console.error('[chat]', data.message || 'Unknown chat error');
      window.alert(data.message || 'Xabar yuborilmadi. Qayta urinib ko‘ring.');
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
    });
    state.socket.addEventListener('error', (event) => {
      console.error('[chat] websocket error', event);
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

      const userResponse = await fetch('/profile/');
      if (userResponse.ok) {
        const pageText = await userResponse.text();
        const match = pageText.match(/"id":(\d+)/);
        if (match) state.userInfo = { id: Number(match[1]) };
      }
    } catch (error) {
      console.error('[chat] history fetch failed', error);
    }
  }

  function sendMessage(message) {
    if (!message || !message.trim()) return;
    if (state.isSending) return;

    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
      throw new Error('Chat serverga ulanmagan. Sahifani yangilang yoki keyinroq urinib ko‘ring.');
    }

    state.socket.send(JSON.stringify({
      type: 'message',
      text: message.trim(),
      reply_to: state.replyToMessageId || null,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    event.stopPropagation();

    const message = input.value.trim();
    if (!message) {
      input.focus();
      return;
    }

    setSendState(true);

    try {
      sendMessage(message);
      input.value = '';
      input.style.height = 'auto';
      if (typingIndicator) {
        typingIndicator.dataset.typingUsers = '';
        typingIndicator.textContent = '';
        typingIndicator.classList.add('hidden');
      }
      sendTypingEvent(false);
    } catch (error) {
      console.error('[chat] send failed', error);
      window.alert(error.message || 'Xabar yuborilmadi. Qayta urinib ko‘ring.');
    } finally {
      setSendState(false);
    }
  }

  form.addEventListener('submit', handleSubmit);

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (input.value.trim()) {
        form.requestSubmit();
      }
      return;
    }
  });

  input.addEventListener('input', () => {
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
  });

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
        window.alert(result.error || 'Image upload failed');
        return;
      }

      imageInput.value = '';
      input.value = '';
      sendTypingEvent(false);
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
        window.alert(result.error || 'Audio upload failed');
        return;
      }

      audioInput.value = '';
      input.value = '';
      sendTypingEvent(false);
    });
  }

  messagesContainer.addEventListener('scroll', updateScrollState);
  setSendState(false);
  prepareSocket();
});
