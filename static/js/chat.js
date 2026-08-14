const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const onlineCountEl = document.getElementById('online-count');
const emptyChat = document.getElementById('empty-chat');
const replyPreview = document.getElementById('reply-preview');
const typingIndicator = document.getElementById('typing-indicator');
const imageButton = document.getElementById('image-button');
const audioButton = document.getElementById('audio-button');
const imageInput = document.getElementById('image-input');
const audioInput = document.getElementById('audio-input');
const sendButton = document.querySelector('.send-button');

let socket = null;
let typingTimer = null;
let replyToMessageId = null;
let userInfo = null;
let latestMessageId = null;
let isNearBottom = true;

function setSendLoading(isLoading) {
  if (!sendButton) return;
  sendButton.disabled = isLoading;
  sendButton.setAttribute('aria-busy', String(isLoading));
  const defaultText = sendButton.dataset.defaultText || 'Yuborish';
  sendButton.dataset.defaultText = defaultText;
  sendButton.textContent = isLoading ? 'Yuborilmoqda...' : defaultText;
}

function showChatError(message) {
  console.error(message);
  alert(message);
}

function escapeHtml(value = '') {
  return value
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

function renderMessage(message, prepend = false) {
  if (!message || message.is_deleted) return;

  const wrapper = document.createElement('article');
  wrapper.className = 'message';
  if (message.sender_id === userInfo?.id) wrapper.classList.add('own');
  wrapper.dataset.messageId = message.id;

  const row = document.createElement('div');
  row.className = 'message-row';

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  if (message.sender_avatar) {
    avatar.innerHTML = `<img src="${message.sender_avatar}" alt="${escapeHtml(message.sender_name || 'User')}" />`;
  } else {
    const initials = (message.sender_name || 'U').split(' ').slice(0,2).map(word => word[0]).join('').toUpperCase();
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

  if (prepend) {
    chatMessages.prepend(wrapper);
  } else {
    chatMessages.appendChild(wrapper);
  }

  if (message.id && (!latestMessageId || message.id > latestMessageId)) {
    latestMessageId = message.id;
  }

  if (emptyChat) emptyChat.classList.add('hidden');
}

function setReplyPreview(message) {
  if (!message) {
    replyPreview.classList.add('hidden');
    replyPreview.innerHTML = '';
    replyToMessageId = null;
    return;
  }

  replyToMessageId = message.id;
  replyPreview.innerHTML = `
    <div class="reply-preview-head">
      <strong>${escapeHtml(message.sender_name || 'User')}</strong>
      <button type="button" class="reply-cancel">✕</button>
    </div>
    <div>${escapeHtml((message.text || '').slice(0, 120))}</div>
  `;
  replyPreview.classList.remove('hidden');
  replyPreview.querySelector('.reply-cancel').addEventListener('click', () => setReplyPreview(null));
}

function updateScrollState() {
  const nearBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 120;
  isNearBottom = nearBottom;
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingUser(username, isTyping) {
  if (!username) return;
  const typingUsers = new Map();
  const current = typingIndicator.dataset.typingUsers || '';
  const users = current ? current.split('|').filter(Boolean) : [];
  if (isTyping) {
    if (!users.includes(`${username}`)) users.push(username);
  } else {
    const filtered = users.filter(user => user !== username);
    if (filtered.length) {
      typingIndicator.dataset.typingUsers = filtered.join('|');
    } else {
      typingIndicator.dataset.typingUsers = '';
    }
  }
  const names = typingIndicator.dataset.typingUsers ? typingIndicator.dataset.typingUsers.split('|').filter(Boolean) : [];
  if (names.length) {
    typingIndicator.textContent = `${names.join(', ')} yozmoqda...`;
    typingIndicator.classList.remove('hidden');
  } else {
    typingIndicator.textContent = '';
    typingIndicator.classList.add('hidden');
  }
}

function sendTypingEvent(isTyping) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ type: 'typing', is_typing: isTyping }));
}

function handleSocketMessage(event) {
  const data = JSON.parse(event.data);

  if (data.type === 'presence') {
    onlineCountEl.textContent = `${data.online_count} online`;
    return;
  }

  if (data.type === 'new_message') {
    renderMessage(data.message);
    if (isNearBottom) scrollToBottom();
    return;
  }

  if (data.type === 'typing') {
    addTypingUser(data.username, data.is_typing);
    return;
  }

  if (data.type === 'delete_message') {
    const el = document.querySelector(`[data-message-id="${data.message_id}"]`);
    if (el) el.remove();
    return;
  }

  if (data.type === 'error') {
    alert(data.message || 'Xatolik');
  }
}

function prepareSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${protocol}://${window.location.host}/ws/chat/`;
  socket = new WebSocket(url);
  socket.addEventListener('message', handleSocketMessage);
  socket.addEventListener('open', () => {
    setSendLoading(false);
    fetchHistory();
  });
  socket.addEventListener('error', (event) => {
    console.error('WebSocket error:', event);
    showChatError('WebSocket xatosi: ulanish o\'chdi. Sahifani yangilang yoki keyinroq urinib ko\'ring.');
    setSendLoading(false);
  });
  socket.addEventListener('close', () => {
    setSendLoading(false);
    setTimeout(prepareSocket, 1500);
  });
}

async function fetchHistory() {
  try {
    const res = await fetch('/chat/history/?page=1');
    if (!res.ok) throw new Error('History failed');
    const result = await res.json();
    const messages = result.messages || [];
    if (!messages.length) {
      emptyChat.classList.remove('hidden');
      return;
    }
    chatMessages.innerHTML = '';
    messages.forEach(message => renderMessage(message));
    scrollToBottom();
    const userRes = await fetch('/profile/');
    if (userRes.ok) {
      const text = await userRes.text();
      const match = text.match(/"id":(\d+)/);
      if (match) userInfo = { id: Number(match[1]) };
    }
  } catch (error) {
    console.error(error);
  }
}

function sendMessage(text, replyId = null) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    throw new Error('WebSocket not connected. Please refresh the page and try again.');
  }

  socket.send(JSON.stringify({
    type: 'message',
    text,
    reply_to: replyId,
  }));
}

chatForm.addEventListener('submit', function (event) {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  setSendLoading(true);

  try {
    sendMessage(text, replyToMessageId);
    chatInput.value = '';
    setReplyPreview(null);
    sendTypingEvent(false);
  } catch (error) {
    console.error('Chat send failed:', error);
    showChatError(error.message || 'Xabar yuborishda xatolik yuz berdi.');
  } finally {
    setSendLoading(false);
  }
});

chatInput.addEventListener('input', () => {
  const hasText = chatInput.value.trim().length > 0;
  if (hasText) {
    sendTypingEvent(true);
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => sendTypingEvent(false), 1200);
  } else {
    sendTypingEvent(false);
  }
});

chatInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

imageButton.addEventListener('click', () => imageInput.click());
audioButton.addEventListener('click', () => audioInput.click());

imageInput.addEventListener('change', async () => {
  const file = imageInput.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('image', file);
  if (chatInput.value.trim()) form.append('text', chatInput.value.trim());
  const response = await fetch('/chat/upload/', { method: 'POST', headers: { 'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] }, body: form });
  const result = await response.json();
  if (!response.ok) {
    alert(result.error || 'Image upload failed');
    return;
  }
  imageInput.value = '';
  chatInput.value = '';
  sendTypingEvent(false);
});

audioInput.addEventListener('change', async () => {
  const file = audioInput.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('audio', file);
  if (chatInput.value.trim()) form.append('text', chatInput.value.trim());
  const response = await fetch('/chat/upload/', { method: 'POST', headers: { 'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] }, body: form });
  const result = await response.json();
  if (!response.ok) {
    alert(result.error || 'Audio upload failed');
    return;
  }
  audioInput.value = '';
  chatInput.value = '';
  sendTypingEvent(false);
