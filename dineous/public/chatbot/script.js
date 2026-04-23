const input = document.getElementById("user-input");
const btn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const messages = document.getElementById("chat-messages");
const chatToggle = document.getElementById("chat-toggle");
const chatContainer = document.getElementById("chat-container");
const minimizeBtn = document.getElementById("minimize-btn");
const resetBtn = document.getElementById("reset-btn");

let isSending = false;

// ===== FOOD EMOJIS for items =====
const FOOD_EMOJIS = {
  pizza: '🍕', burger: '🍔', pasta: '🍝', salad: '🥗', soup: '🍲',
  sandwich: '🥪', taco: '🌮', sushi: '🍣', ramen: '🍜', rice: '🍚',
  chicken: '🍗', steak: '🥩', fish: '🐟', shrimp: '🍤', wrap: '🌯',
  fries: '🍟', nachos: '🧀', wings: '🍗', ribs: '🍖', noodle: '🍜',
  dosa: '🫓', idli: '🫓', biryani: '🍛', curry: '🍛', paneer: '🧀',
  naan: '🫓', dal: '🫕', samosa: '🥟', chai: '☕', coffee: '☕',
  tea: '🍵', juice: '🧃', coke: '🥤', water: '💧', lassi: '🥛',
  icecream: '🍦', cake: '🎂', brownie: '🍫', gulab: '🍮', halwa: '🍮',
  pickles: '🥒', dip: '🫕', artichoke: '🥦', onion: '🧅',
  leek: '🌿', caesar: '🥗', french: '🧅', potato: '🥔', house: '🏠',
  bacon: '🥓', fried: '🍳', default: '🍽️'
};

function getFoodEmoji(itemName) {
  const lower = itemName.toLowerCase();
  for (const [key, emoji] of Object.entries(FOOD_EMOJIS)) {
    if (lower.includes(key)) return emoji;
  }
  return FOOD_EMOJIS.default;
}

// ===== RESTAURANT BANNER COLORS =====
const RESTAURANT_PALETTES = [
  'linear-gradient(135deg, #2d1a0a, #7c3a00, #c44d00)',
  'linear-gradient(135deg, #0a1628, #1e3a6e, #2563eb)',
  'linear-gradient(135deg, #0a1f0a, #1a4a1a, #16a34a)',
  'linear-gradient(135deg, #1a0a1f, #4a1a6e, #7c3aed)',
  'linear-gradient(135deg, #1f0a0a, #6e1a1a, #dc2626)',
  'linear-gradient(135deg, #0a1a1f, #1a4a6e, #0891b2)',
];

const RESTAURANT_EMOJIS = ['🍽️', '🥘', '🫕', '🍲', '🥗', '🍛', '🍜', '🏮', '🎌', '🫙'];

// ===== APPEND PLAIN TEXT MESSAGE =====
function appendMessage(sender, text) {
  const wrapper = document.createElement("div");
  wrapper.className = sender === "user" ? "message user-msg" : "message bot-msg";

  if (sender === "bot") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = `<img src="/chatbot/assets/bot-face.png" alt="DineBot">`;
    wrapper.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  const time = document.createElement("div");
  time.className = "time";
  time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// ===== APPEND RICH CARD (bot only) =====
function appendCard(cardHTML) {
  const wrapper = document.createElement("div");
  wrapper.className = "message bot-msg";
  wrapper.style.flexDirection = "column";
  wrapper.style.alignItems = "flex-start";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.style.marginBottom = "6px";
  avatar.innerHTML = `<img src="/chatbot/assets/bot-face.png" alt="DineBot">`;

  const cardWrapper = document.createElement("div");
  cardWrapper.style.maxWidth = "90%";
  cardWrapper.style.width = "100%";
  cardWrapper.innerHTML = cardHTML;

  const time = document.createElement("div");
  time.className = "time";
  time.style.marginLeft = "0";
  time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  wrapper.appendChild(avatar);
  wrapper.appendChild(cardWrapper);
  wrapper.appendChild(time);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;

  return cardWrapper;
}

// ===== RENDER RESTAURANT CARDS =====
function renderRestaurantCards(restaurants) {
  const html = `
    <div class="restaurant-cards">
      ${restaurants.map((r, i) => {
        const palette = RESTAURANT_PALETTES[i % RESTAURANT_PALETTES.length];
        const emoji = RESTAURANT_EMOJIS[i % RESTAURANT_EMOJIS.length];
        return `
          <div class="restaurant-card">
            <div class="restaurant-card-banner" style="background: ${palette}">
              <span class="restaurant-emoji">${emoji}</span>
              <span class="restaurant-badge">#${r.id}</span>
            </div>
            <div class="restaurant-card-body">
              <div class="restaurant-card-title">${r.name}</div>
              <div class="restaurant-card-meta">
                <span class="restaurant-meta-item">📍 ${r.location || 'City Center'}</span>
                <span class="restaurant-meta-item">⭐ ${(4 + Math.random()).toFixed(1)}</span>
                <span class="restaurant-meta-item">🕐 25-35 min</span>
              </div>
              <button class="restaurant-select-btn" onclick="selectRestaurant(${r.id}, '${r.name}')">
                Select Restaurant <span>→</span>
              </button>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;

  appendMessage("bot", "🍽️ Here are our restaurants — pick your favourite!");
  appendCard(html);
}

// ===== RENDER MENU CARDS =====
function renderMenuCards(menuItems, priceMap) {
  const items = Array.isArray(menuItems)
    ? menuItems
    : Object.keys(priceMap || {}).map(name => ({ item_name: name, price: priceMap[name] }));

  const html = `
    <div style="width:100%">
      <div class="menu-section-title">🍴 Today's Menu</div>
      <div class="menu-grid">
        ${items.map(item => {
          const name = item.item_name || item.name || 'Item';
          const price = item.price || 0;
          const emoji = getFoodEmoji(name);
          return `
            <div class="menu-item-card" onclick="orderItem('${name}')">
              <div class="menu-item-left">
                <div class="menu-item-icon">${emoji}</div>
                <div class="menu-item-info">
                  <div class="menu-item-name">${name.charAt(0).toUpperCase() + name.slice(1)}</div>
                  <div class="menu-item-desc">Freshly prepared</div>
                </div>
              </div>
              <div class="menu-item-right">
                <div class="menu-item-price">₹${price}</div>
                <button class="menu-add-btn" onclick="event.stopPropagation(); orderItem('${name}')">+</button>
              </div>
            </div>
          `;
        }).join('')}
      </div>
      <div style="margin-top:10px;font-size:11.5px;color:#999;text-align:center;font-style:italic;">Tap any item to add to cart</div>
    </div>
  `;

  appendCard(html);
}

// ===== RENDER CART =====
function renderCart(cartItems, total) {
  const html = `
    <div class="cart-display">
      <div class="cart-header-strip">
        <span>🛒</span>
        <span>Your Cart</span>
      </div>
      <div class="cart-items-list">
        ${cartItems.map(item => `
          <div class="cart-item-row">
            <span class="cart-item-name">${item.name.charAt(0).toUpperCase() + item.name.slice(1)}</span>
            <span class="cart-item-qty">×${item.qty}</span>
            <span class="cart-item-price">₹${(item.price * item.qty).toFixed(0)}</span>
          </div>
        `).join('')}
      </div>
      <div class="cart-total-row">
        <span class="cart-total-label">Total</span>
        <span class="cart-total-amount">₹${total}</span>
      </div>
      <button class="cart-confirm-btn" onclick="sendMessage('confirm order')">
        ✓ Confirm Order
      </button>
    </div>
  `;
  appendCard(html);
}

// ===== RENDER ORDER CONFIRMED =====
function renderOrderConfirmed(orderId, items, total) {
  const html = `
    <div class="order-confirmed-card">
      <div class="order-confirmed-header">
        <span class="order-confirmed-icon">🎉</span>
        <div class="order-confirmed-title">Order Confirmed!</div>
        <div class="order-id-badge">📋 Order #${orderId}</div>
      </div>
      <div class="order-confirmed-body">
        <div class="order-items-mini">
          ${items.map(i => `
            <div class="order-item-mini-row">
              ${i.qty}× ${i.name.charAt(0).toUpperCase() + i.name.slice(1)} — <strong>₹${(i.qty * i.price).toFixed(0)}</strong>
            </div>
          `).join('')}
        </div>
        <div class="order-eta-strip">
          <div class="order-eta-left">⏱️ Estimated delivery</div>
          <div class="order-eta-time">30–40 min</div>
        </div>
        <div style="font-size:12px;color:#666;text-align:center;margin-bottom:8px;">
          💰 Total Paid: <strong style="color:#e85d04">₹${total}</strong>
        </div>
        <button class="order-track-btn" onclick="sendMessage('track ${orderId}')">
          📦 Track Order #${orderId}
        </button>
      </div>
    </div>
  `;
  appendCard(html);
}

// ===== RENDER ORDER STATUS =====
const STATUS_PROGRESS = {
  pending: 10, accepted: 25, preparing: 50, ready: 70,
  out_for_delivery: 85, picked_up: 90, delivered: 100,
  completed: 100, rejected: 0
};

const STATUS_LABELS = {
  pending: 'Pending', accepted: 'Accepted', preparing: 'Preparing',
  ready: 'Ready', out_for_delivery: 'On Way', picked_up: 'Picked Up',
  delivered: 'Delivered', completed: 'Done', rejected: 'Cancelled'
};

function renderOrderStatus(order) {
  const status = order.status || 'pending';
  const progress = STATUS_PROGRESS[status] || 0;
  const items = order.items || [];
  const total = order.total_price || order.total || 0;
  const steps = ['Accepted', 'Preparing', 'Ready', 'Delivered'];

  const html = `
    <div class="order-status-card">
      <div class="order-status-header">
        <span class="order-status-id">Order #${order.id || order.order_id}</span>
        <span class="status-pill ${status}">${STATUS_LABELS[status] || status}</span>
      </div>
      ${status !== 'rejected' ? `
      <div class="order-progress-bar">
        <div class="progress-track">
          <div class="progress-fill" style="width: ${progress}%"></div>
        </div>
        <div class="progress-steps">
          ${steps.map(s => `<span class="progress-step ${STATUS_LABELS[status] === s || (status==='accepted' && s==='Accepted') ? 'active' : ''}">${s}</span>`).join('')}
        </div>
      </div>` : ''}
      <div class="order-status-body">
        <div style="font-size:12px;color:#666;margin-bottom:6px;font-weight:500;">Items ordered:</div>
        <div style="display:flex;flex-direction:column;gap:3px;">
          ${items.map(i => `
            <div style="font-size:12.5px;color:#333;display:flex;justify-content:space-between;">
              <span>${i.qty}× ${i.name.charAt(0).toUpperCase() + i.name.slice(1)}</span>
              <span style="color:#e85d04;font-weight:600;">₹${(i.qty * i.price).toFixed(0)}</span>
            </div>
          `).join('')}
        </div>
        <div style="margin-top:10px;padding-top:8px;border-top:1px solid #e8e6e1;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:11px;color:#999;text-transform:uppercase;letter-spacing:0.5px;">Total</span>
          <span style="font-size:15px;font-weight:700;color:#e85d04;font-family:'Playfair Display',serif;">₹${total}</span>
        </div>
      </div>
    </div>
  `;
  appendCard(html);
}

// ===== QUICK ACTIONS =====
const QUICK_ACTIONS = [
  { id: "view_restaurants", label: "🍽️ View Restaurants" },
  { id: "book_table", label: "🪑 Book a Table" },
  { id: "help_faqs", label: "❓ Help & FAQs" },
  { id: "just_chat", label: "💬 Just Chat" }
];

function appendOptions(options) {
  const wrapper = document.createElement("div");
  wrapper.className = "message bot-msg";
  wrapper.style.flexDirection = "column";
  wrapper.style.alignItems = "flex-start";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.style.marginBottom = "6px";
  avatar.innerHTML = `<img src="/chatbot/assets/bot-face.png" alt="DineBot">`;
  wrapper.appendChild(avatar);

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.style.maxWidth = "88%";

  options.forEach(opt => {
    const b = document.createElement("button");
    b.className = "chat-option-btn";
    b.textContent = opt.label;
    b.onclick = () => handleQuickAction(opt.id);
    bubble.appendChild(b);
  });

  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

function handleQuickAction(actionId) {
  const action = QUICK_ACTIONS.find(a => a.id === actionId);
  if (action) sendMessage(action.label);
}

// ===== GLOBAL CLICK HANDLERS =====
window.selectRestaurant = function(id, name) {
  sendMessage(String(id));
};

window.orderItem = function(name) {
  sendMessage(`1 ${name}`);
};

// ===== PARSE RESPONSE & RENDER RICH UI =====
function handleBotResponse(data, message) {
  const reply = data.reply || "";
  const intent = data.intent || "";
  const lowerReply = reply.toLowerCase();

  // RESTAURANTS LIST — detect from response
  if (intent === "view_restaurants" || (intent === "select_restaurant" && reply.includes("Invalid"))) {
    // Try to parse restaurant list from reply
    const lines = reply.split('\n').filter(l => l.trim());
    const restaurants = [];
    lines.forEach(line => {
      const match = line.match(/^(\d+)\.\s+(.+?)\s+\((.+?)\)/);
      if (match) {
        restaurants.push({ id: parseInt(match[1]), name: match[2].trim(), location: match[3].trim() });
      }
    });
    if (restaurants.length > 0) {
      renderRestaurantCards(restaurants);
      return;
    }
  }

  // RESTAURANT SELECTED
  if (intent === "select_restaurant" && reply.includes("Selected")) {
    appendMessage("bot", reply);
    return;
  }

  // MENU — detect menu items in reply
  if (intent === "menu" || (reply.includes("Menu:") && reply.includes("₹"))) {
    const items = [];
    const lines = reply.split('\n');
    lines.forEach(line => {
      const match = line.match(/\d+\.\s+(.+?)\s+-\s+₹([\d.]+)/i);
      if (match) {
        items.push({ item_name: match[1].trim(), price: parseFloat(match[2]) });
      }
    });
    if (items.length > 0) {
      appendMessage("bot", "Here's what we're serving today 🍽️");
      renderMenuCards(items);
      return;
    }
  }

  // CART — detect cart summary
  if (reply.includes("Added to cart") && reply.includes("Cart:")) {
    // Parse cart items from text
    const cartItems = [];
    const totalMatch = reply.match(/Total:\s*₹([\d.]+)/);
    const total = totalMatch ? totalMatch[1] : '0';

    const itemLines = reply.split('\n').filter(l => l.includes('×') || l.includes('x '));
    itemLines.forEach(line => {
      const m = line.match(/•\s*(\d+)x\s+(.+?)\s+-\s+₹([\d.]+)/i);
      if (m) {
        cartItems.push({ qty: parseInt(m[1]), name: m[2].trim(), price: parseFloat(m[3]) / parseInt(m[1]) });
      }
    });

    if (cartItems.length > 0) {
      renderCart(cartItems, total);
      return;
    }
  }

  // ORDER CONFIRMED
  if (intent === "confirm_order" && reply.includes("Order Confirmed")) {
    const orderIdMatch = reply.match(/Order ID:\s*\*?\*?(\d+)\*?\*?/);
    const totalMatch = reply.match(/Total:\s*₹([\d.]+)/);
    const orderId = orderIdMatch ? orderIdMatch[1] : '?';
    const total = totalMatch ? totalMatch[1] : '0';

    // Parse items
    const items = [];
    const itemLines = reply.split('\n');
    itemLines.forEach(line => {
      const m = line.match(/•\s*(\d+)x\s+(.+)/i);
      if (m) items.push({ qty: parseInt(m[1]), name: m[2].trim(), price: parseFloat(total) / parseInt(m[1]) });
    });

    renderOrderConfirmed(orderId, items.length > 0 ? items : [{ qty: 1, name: 'Item', price: parseFloat(total) }], total);
    return;
  }

  // ORDER STATUS / TRACK
  if (intent === "track_order" && reply.includes("Order #")) {
    const orderIdMatch = reply.match(/Order #(\d+)/);
    const statusMatch = reply.match(/Status:\s*\*?\*?(\w+)\*?\*?/i);
    const totalMatch = reply.match(/Total:\s*₹([\d.]+)/);
    const orderId = orderIdMatch ? orderIdMatch[1] : '?';
    const status = statusMatch ? statusMatch[1].toLowerCase() : 'pending';

    const items = [];
    const itemLines = reply.split('\n');
    itemLines.forEach(line => {
      const m = line.match(/•\s*(\d+)x\s+(.+)/i);
      if (m) items.push({ qty: parseInt(m[1]), name: m[2].trim(), price: 0 });
    });

    renderOrderStatus({
      id: orderId,
      status: status,
      items: items,
      total_price: totalMatch ? totalMatch[1] : 0
    });
    return;
  }

  // ORDER CANCELLED
  if (intent === "cancel_order" && reply.includes("cancelled")) {
    appendCard(`
      <div style="background:#fff1f2;border:1.5px solid #fecdd3;border-radius:12px;padding:14px;text-align:center;">
        <div style="font-size:22px;margin-bottom:6px;">❌</div>
        <div style="font-size:13px;font-weight:600;color:#be123c;">Order Cancelled</div>
        <div style="font-size:12px;color:#9f1239;margin-top:4px;">${reply.replace('❌', '').trim()}</div>
      </div>
    `);
    return;
  }

  // DEFAULT — plain text with cleaned markdown
  const cleaned = reply
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1');
  appendMessage("bot", cleaned);
}

// ===== SEND MESSAGE =====
async function sendMessage(customText = null, forceAppend = false) {
  const text = String(customText ?? input.value).trim();
  if (!text || isSending) return;

  isSending = true;
  appendMessage("user", text);
  if (customText == null) input.value = "";
  showTyping();

  try {
    const res = await fetch("http://localhost:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "harshit", message: text }),
    });

    if (!res.ok) throw new Error("Network response not OK");
    const data = await res.json();
    hideTyping();

    handleBotResponse(data, text);

    if (data.speak === true) {
      const textToSpeak = data.speech_text || data.reply;
      speak(textToSpeak);
    }

  } catch (err) {
    hideTyping();
    console.error("Send error:", err);
    appendMessage("bot", "⚠️ Connection issue. Please try again.");
  } finally {
    setTimeout(() => { isSending = false; }, 300);
  }
}

// ===== SPEAK =====
function speak(text) {
  if (!text) return;
  try { window.speechSynthesis.cancel(); } catch (e) {}
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-IN";
  window.speechSynthesis.speak(u);
}

// ===== VOICE =====
let recognition = null;
let autoSend = true;
let lastTranscript = "";
let lastTime = 0;

let toggleBtn = document.getElementById("auto-toggle");
if (!toggleBtn) {
  toggleBtn = document.createElement("button");
  toggleBtn.id = "auto-toggle";
  toggleBtn.textContent = "🎙️ Auto Send ON";
  toggleBtn.className = "toggle-btn";
  const chatInputEl = document.querySelector(".chat-input") || document.body;
  chatInputEl.appendChild(toggleBtn);
}

toggleBtn.addEventListener("click", () => {
  autoSend = !autoSend;
  toggleBtn.textContent = autoSend ? "🎙️ Auto Send ON" : "🎙️ Manual Mode";
  toggleBtn.classList.toggle("off", !autoSend);
});

const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition || null;

async function ensureMicPermission() {
  if (!navigator.mediaDevices?.getUserMedia) return false;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach(t => t.stop());
    return true;
  } catch (err) {
    alert("Please allow microphone access to use voice input.");
    return false;
  }
}

async function createRecognitionInstance() {
  if (!SpeechRec) return null;
  const ok = await ensureMicPermission();
  if (!ok) return null;

  try {
    const r = new SpeechRec();
    r.lang = "en-IN";
    r.interimResults = true;
    r.continuous = true;
    r.maxAlternatives = 1;

    r.onstart = () => {
      micBtn.textContent = "🎙️";
      micBtn.classList.add("listening");
      micBtn.style.backgroundColor = "#ff4444";
    };

    r.onend = () => {
      micBtn.textContent = "🎤";
      micBtn.classList.remove("listening");
      micBtn.style.backgroundColor = "";
    };

    r.onresult = (e) => {
      try {
        const resultIndex = e.results.length - 1;
        const transcript = String(e.results[resultIndex][0].transcript || "").trim();
        if (!transcript) return;
        const now = Date.now();
        if (transcript.toLowerCase() === lastTranscript.toLowerCase() && now - lastTime < 1500) return;
        lastTranscript = transcript;
        lastTime = now;
        if (autoSend) {
          setTimeout(() => sendMessage(transcript, true), 600);
        } else {
          input.value = transcript;
        }
        recognition.stop();
      } catch (err) { console.error("Recognition result error:", err); }
    };

    r.onerror = (err) => {
      micBtn.style.backgroundColor = "";
      if (err?.error === "not-allowed") alert("❌ Microphone access denied!");
      micBtn.textContent = "🎤";
      micBtn.classList.remove("listening");
    };

    return r;
  } catch (err) { return null; }
}

if (!SpeechRec) {
  micBtn.addEventListener("click", () => {
    alert("❌ Speech not supported.\nPlease use Chrome or Edge.");
  });
} else {
  micBtn.addEventListener("click", async () => {
    if (!recognition) {
      recognition = await createRecognitionInstance();
      if (!recognition) return;
    }
    try { recognition.abort(); } catch (e) {}
    recognition.start();
  });
}

// ===== TOGGLE CHAT =====
chatToggle.addEventListener("click", () => {
  chatContainer.classList.toggle("open");
});

minimizeBtn.addEventListener("click", () => {
  chatContainer.classList.remove("open");
});

resetBtn.addEventListener("click", () => {
  hideTyping();
  messages.innerHTML = "";
  appendMessage("bot", "Hi 👋 I'm DineBot.\nHow can I help you today?");
  appendOptions(QUICK_ACTIONS);
});

// ===== INPUT EVENTS =====
btn.addEventListener("click", () => sendMessage());
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});

// ===== INIT =====
window.addEventListener("DOMContentLoaded", () => {
  appendMessage("bot", "Hi 👋 I'm DineBot. Welcome!");
  appendOptions(QUICK_ACTIONS);
});

// ===== TYPING INDICATOR =====
let typingBubble = null;

function showTyping() {
  if (typingBubble) return;
  typingBubble = document.createElement("div");
  typingBubble.className = "message bot-msg";
  typingBubble.innerHTML = `
    <div class="avatar"><img src="/chatbot/assets/bot-face.png" alt="DineBot"></div>
    <div class="bubble typing">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>
  `;
  messages.appendChild(typingBubble);
  messages.scrollTop = messages.scrollHeight;
}

function hideTyping() {
  if (typingBubble) {
    typingBubble.remove();
    typingBubble = null;
  }
}

