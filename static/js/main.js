function fmt(n) {
  return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + 'đ';
}

function updateCartCount() {
  fetch('/cart/count').then(r => r.json()).then(d => {
    document.getElementById('cartCount').textContent = d.count;
  });
}

let searchTimeout;
const searchInput = document.getElementById('searchInput');
const searchDropdown = document.getElementById('searchDropdown');

if (searchInput) {
  searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const q = this.value.trim();
    if (q.length < 1) { searchDropdown.classList.remove('show'); return; }
    searchTimeout = setTimeout(() => {
      fetch('/api/search-suggest?q=' + encodeURIComponent(q))
        .then(r => r.json())
        .then(items => {
          if (!items.length) { searchDropdown.classList.remove('show'); return; }
          searchDropdown.innerHTML = items.map(p => `
            <div class="search-item" onclick="location.href='/product/${p.id}'">
              <img src="${p.image}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/40'">
              <span class="search-item-name">${p.name}</span>
              <span class="search-item-price">${fmt(p.sale_price || p.price)}</span>
            </div>
          `).join('');
          searchDropdown.classList.add('show');
        });
    }, 200);
  });

  searchInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') doSearch();
  });

  document.addEventListener('click', function(e) {
    if (!e.target.closest('.search-box')) searchDropdown.classList.remove('show');
  });
}

function doSearch() {
  const q = document.getElementById('searchInput').value.trim();
  if (q) location.href = '/products?q=' + encodeURIComponent(q);
}

function addToCart(pid, qty) {
  qty = qty || 1;
  const fd = new FormData();
  fd.append('product_id', pid);
  fd.append('quantity', qty);
  fetch('/cart/add', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        updateCartCount();
        showToast('Đã thêm vào giỏ hàng! 🛒');
      }
    });
}

function toggleWishlist(pid, btn) {
  const fd = new FormData();
  fd.append('product_id', pid);
  fetch('/wishlist/toggle', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(d => {
      if (btn) {
        btn.textContent = d.added ? '❤️' : '🤍';
        btn.classList.toggle('active', d.added);
      }
      showToast(d.added ? 'Đã thêm vào yêu thích ❤️' : 'Đã bỏ khỏi yêu thích');
    });
}

function showToast(msg, type) {
  const div = document.createElement('div');
  div.className = `flash flash-${type || 'success'}`;
  div.textContent = msg;
  let container = document.querySelector('.flash-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
  }
  container.appendChild(div);
  setTimeout(() => div.remove(), 3000);
}

function toggleChat() {
  const box = document.getElementById('chatbotBox');
  box.style.display = box.style.display === 'none' ? 'flex' : 'none';
  if (box.style.display !== 'none') box.style.flexDirection = 'column';
}

function sendChat() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  const msgs = document.getElementById('chatMessages');
  msgs.innerHTML += `<div class="user-msg">${msg}</div>`;
  msgs.scrollTop = msgs.scrollHeight;
  const typing = document.createElement('div');
  typing.className = 'bot-msg';
  typing.textContent = '...';
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;
  fetch('/api/chatbot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg })
  }).then(r => r.json()).then(d => {
    typing.textContent = d.reply;
    if (d.products) {
      d.products.forEach(p => {
        const el = document.createElement('div');
        el.className = 'bot-msg';
        el.innerHTML = `<a href="/product/${p.id}" style="color:var(--primary);text-decoration:underline;">${p.name}</a>`;
        msgs.appendChild(el);
      });
    }
    msgs.scrollTop = msgs.scrollHeight;
  });
}

function updateQty(pid, delta) {
  const inp = document.getElementById('qty-' + pid);
  let v = parseInt(inp.value) + delta;
  if (v < 1) v = 1;
  inp.value = v;
  const fd = new FormData();
  fd.append('product_id', pid);
  fd.append('quantity', v);
  fetch('/cart/update', { method: 'POST', body: fd }).then(() => location.reload());
}

function removeCart(pid) {
  const fd = new FormData();
  fd.append('product_id', pid);
  fetch('/cart/remove', { method: 'POST', body: fd }).then(() => location.reload());
}

function startCountdown(endTime) {
  function update() {
    const now = new Date().getTime();
    const end = new Date(endTime).getTime();
    const diff = end - now;
    if (diff <= 0) { document.getElementById('countdown-h').textContent = '00'; return; }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    const hEl = document.getElementById('countdown-h');
    const mEl = document.getElementById('countdown-m');
    const sEl = document.getElementById('countdown-s');
    if (hEl) hEl.textContent = h.toString().padStart(2, '0');
    if (mEl) mEl.textContent = m.toString().padStart(2, '0');
    if (sEl) sEl.textContent = s.toString().padStart(2, '0');
  }
  update();
  setInterval(update, 1000);
}

function selectPayment(type) {
  document.querySelectorAll('.payment-card').forEach(c => c.classList.remove('selected'));
  event.currentTarget.classList.add('selected');
  document.getElementById('cardForm').classList.toggle('show', type === 'card');
  document.getElementById('paymentMethod').value = type;
}

function submitCheckout() {
  const name = document.getElementById('recv_name')?.value;
  const phone = document.getElementById('recv_phone')?.value;
  const address = document.getElementById('recv_address')?.value;
  if (!name || !phone || !address) { showToast('Vui lòng điền đầy đủ thông tin giao hàng', 'error'); return; }
  const fd = new FormData();
  fd.append('name', name);
  fd.append('phone', phone);
  fd.append('address', address);
  fd.append('payment_method', document.getElementById('paymentMethod')?.value || 'cod');
  fetch('/checkout', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        document.getElementById('orderSuccessModal').classList.add('show');
        document.getElementById('successOrderId').textContent = '#' + d.order_id;
      }
    });
}

function stars(rating) {
  return '★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating));
}

document.addEventListener('DOMContentLoaded', function() {
  updateCartCount();
  const flashEls = document.querySelectorAll('.flash');
  flashEls.forEach(el => setTimeout(() => el.remove(), 4000));
});
