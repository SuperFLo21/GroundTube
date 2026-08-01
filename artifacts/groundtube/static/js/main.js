/* GroundTube — Main JavaScript */

// ───────────────────────────────────────────────
// Flash alerts auto-dismiss
// ───────────────────────────────────────────────
document.querySelectorAll('.alert').forEach(el => {
  const close = el.querySelector('.alert-close');
  if (close) close.addEventListener('click', () => el.remove());
  setTimeout(() => el.remove(), 5000);
});

// ───────────────────────────────────────────────
// User dropdown
// ───────────────────────────────────────────────
const userToggle = document.getElementById('userMenuToggle');
const userDropdown = document.getElementById('userDropdown');
if (userToggle && userDropdown) {
  userToggle.addEventListener('click', e => {
    e.stopPropagation();
    userDropdown.classList.toggle('open');
  });
  document.addEventListener('click', () => userDropdown.classList.remove('open'));
}

// ───────────────────────────────────────────────
// Like / Dislike
// ───────────────────────────────────────────────
const likeBtn = document.getElementById('likeBtn');
const dislikeBtn = document.getElementById('dislikeBtn');
const likeCount = document.getElementById('likeCount');
const dislikeCount = document.getElementById('dislikeCount');
const likeBarFill = document.getElementById('likeBarFill');

function updateLikeBar(likes, dislikes) {
  if (!likeBarFill) return;
  const total = likes + dislikes;
  const pct = total > 0 ? Math.round((likes / total) * 100) : 50;
  likeBarFill.style.width = pct + '%';
}

async function handleLikeDislike(action) {
  const videoId = document.getElementById('videoUUID')?.value;
  if (!videoId) return;
  try {
    const res = await fetch(`/api/like/${videoId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    if (res.status === 401) { window.location = '/login'; return; }
    const data = await res.json();
    if (likeCount) likeCount.textContent = fmtCount(data.likes);
    if (dislikeCount) dislikeCount.textContent = fmtCount(data.dislikes);
    updateLikeBar(data.likes, data.dislikes);
    // Update button state
    likeBtn?.classList.toggle('active', data.user_like === 'like');
    dislikeBtn?.classList.toggle('active', data.user_like === 'dislike');
  } catch (e) { console.error(e); }
}

likeBtn?.addEventListener('click', () => handleLikeDislike('like'));
dislikeBtn?.addEventListener('click', () => handleLikeDislike('dislike'));

// ───────────────────────────────────────────────
// Subscribe
// ───────────────────────────────────────────────
const subBtn = document.getElementById('subscribeBtn');
const subCount = document.getElementById('subCount');

subBtn?.addEventListener('click', async () => {
  const channelId = subBtn.dataset.channelId;
  if (!channelId) return;
  if (!document.body.dataset.loggedIn) { window.location = '/login'; return; }
  try {
    const res = await fetch(`/api/subscribe/${channelId}`, { method: 'POST' });
    if (res.status === 401) { window.location = '/login'; return; }
    const data = await res.json();
    const isSubbed = data.subscribed;
    subBtn.textContent = isSubbed ? 'Subscribed' : 'Subscribe';
    subBtn.classList.toggle('subscribed', isSubbed);
    if (subCount) subCount.textContent = fmtCount(data.count) + ' subscribers';
  } catch (e) { console.error(e); }
});

// ───────────────────────────────────────────────
// Comments
// ───────────────────────────────────────────────
const commentForm = document.getElementById('commentForm');
const commentInput = document.getElementById('commentInput');
const commentSubmit = document.getElementById('commentSubmit');
const commentsList = document.getElementById('commentsList');

if (commentInput) {
  commentInput.addEventListener('input', () => {
    if (commentSubmit) commentSubmit.disabled = !commentInput.value.trim();
  });
  commentInput.addEventListener('focus', () => {
    document.getElementById('commentFormActions')?.classList.remove('hidden');
  });
  document.getElementById('commentCancelBtn')?.addEventListener('click', () => {
    commentInput.value = '';
    if (commentSubmit) commentSubmit.disabled = true;
    document.getElementById('commentFormActions')?.classList.add('hidden');
  });
}

if (commentForm) {
  commentForm.addEventListener('submit', async e => {
    e.preventDefault();
    const content = commentInput?.value.trim();
    if (!content) return;
    const videoId = document.getElementById('videoUUID')?.value;
    if (!videoId) return;
    commentSubmit.disabled = true;
    try {
      const res = await fetch(`/api/comment/${videoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      if (res.status === 401) { window.location = '/login'; return; }
      const data = await res.json();
      if (data.error) { alert(data.error); return; }
      prependComment(data, commentsList);
      commentInput.value = '';
      document.getElementById('commentFormActions')?.classList.add('hidden');
      // Update count
      const cc = document.getElementById('commentCount');
      if (cc) cc.textContent = parseInt(cc.textContent) + 1;
    } catch (e) { console.error(e); }
    finally { commentSubmit.disabled = false; }
  });
}

function prependComment(data, container, isReply = false) {
  const el = document.createElement('div');
  el.className = 'comment';
  el.dataset.commentId = data.id;
  const repliesHtml = isReply ? '' : `
    <div class="comment-actions">
      <button class="btn-reply-toggle" onclick="toggleReplyForm(this, ${data.id})">Reply</button>
    </div>
    <div class="replies" id="replies-${data.id}"></div>`;
  el.innerHTML = `
    <img src="${data.avatar}" alt="" class="comment-avatar" onerror="this.style.display='none'">
    <div class="comment-body">
      <div class="comment-header">
        <span class="comment-username">${escHtml(data.username)}</span>
        <span class="comment-time">${data.time}</span>
      </div>
      <p class="comment-text">${escHtml(data.content)}</p>
      ${repliesHtml}
    </div>`;
  container?.prepend(el);
}

function toggleReplyForm(btn, commentId) {
  const existing = document.getElementById(`reply-form-${commentId}`);
  if (existing) { existing.remove(); return; }

  const form = document.createElement('form');
  form.id = `reply-form-${commentId}`;
  form.className = 'comment-form';
  form.style.marginTop = '8px';
  form.innerHTML = `
    <div class="comment-input-wrap">
      <textarea class="comment-input" rows="1" placeholder="Add a reply…" style="min-height:unset"></textarea>
      <div class="comment-form-actions">
        <button type="button" class="btn-cancel" onclick="document.getElementById('reply-form-${commentId}').remove()">Cancel</button>
        <button type="submit" class="btn-comment">Reply</button>
      </div>
    </div>`;
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const input = form.querySelector('textarea');
    const content = input.value.trim();
    if (!content) return;
    const videoId = document.getElementById('videoUUID')?.value;
    if (!videoId) return;
    try {
      const res = await fetch(`/api/comment/${videoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, parent_id: commentId })
      });
      if (res.status === 401) { window.location = '/login'; return; }
      const data = await res.json();
      if (data.error) { alert(data.error); return; }
      const repliesContainer = document.getElementById(`replies-${commentId}`);
      prependComment(data, repliesContainer, true);
      form.remove();
    } catch (err) { console.error(err); }
  });
  btn.closest('.comment-actions').after(form);
}

async function deleteComment(commentId, el) {
  if (!confirm('Delete this comment?')) return;
  try {
    const res = await fetch(`/api/delete_comment/${commentId}`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      el.closest('.comment')?.remove();
      const cc = document.getElementById('commentCount');
      if (cc) cc.textContent = Math.max(0, parseInt(cc.textContent) - 1);
    }
  } catch (e) { console.error(e); }
}

// ───────────────────────────────────────────────
// Report Modal
// ───────────────────────────────────────────────
const reportModal = document.getElementById('reportModal');

function openReport(type, id) {
  if (!document.body.dataset.loggedIn) { window.location = '/login'; return; }
  if (!reportModal) return;
  reportModal.dataset.type = type;
  reportModal.dataset.id = id;
  reportModal.classList.add('open');
}

function closeReport() { reportModal?.classList.remove('open'); }

document.getElementById('reportSubmitBtn')?.addEventListener('click', async () => {
  const reason = document.getElementById('reportReason')?.value.trim();
  if (!reason) { alert('Please provide a reason.'); return; }
  const type = reportModal.dataset.type;
  const id = reportModal.dataset.id;
  try {
    await fetch('/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_type: type, content_id: id, reason })
    });
    closeReport();
    showToast('Report submitted. Thank you.');
  } catch (e) { console.error(e); }
});

reportModal?.addEventListener('click', e => { if (e.target === reportModal) closeReport(); });

// ───────────────────────────────────────────────
// Video Description expand/collapse
// ───────────────────────────────────────────────
const desc = document.querySelector('.video-description');
if (desc) {
  desc.classList.add('collapsed');
  desc.addEventListener('click', () => desc.classList.toggle('collapsed'));
}

// ───────────────────────────────────────────────
// Upload: drag-and-drop + preview
// ───────────────────────────────────────────────
const dropzone = document.getElementById('uploadDropzone');
const fileInput = document.getElementById('mediaFile');
const fileInfo = document.getElementById('selectedFileInfo');
const uploadForm = document.getElementById('uploadForm');

if (dropzone && fileInput) {
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setSelectedFile(fileInput.files[0]);
  });
}

function setSelectedFile(file) {
  if (fileInput && fileInput !== file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
  }
  if (fileInfo) {
    fileInfo.classList.remove('hidden');
    const name = fileInfo.querySelector('.file-name');
    const size = fileInfo.querySelector('.file-size');
    if (name) name.textContent = file.name;
    if (size) size.textContent = fmtSize(file.size);
  }
}

// Thumbnail preview
const thumbInput = document.getElementById('thumbnailInput');
const thumbPreview = document.getElementById('thumbPreviewImg');
if (thumbInput && thumbPreview) {
  thumbInput.addEventListener('change', () => {
    const file = thumbInput.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = e => { thumbPreview.src = e.target.result; thumbPreview.style.display = 'block'; };
      reader.readAsDataURL(file);
    }
  });
}

// Upload progress simulation
if (uploadForm) {
  uploadForm.addEventListener('submit', () => {
    const progress = document.getElementById('uploadProgress');
    if (progress) {
      progress.style.display = 'block';
      const fill = progress.querySelector('.progress-bar-fill');
      const label = progress.querySelector('.progress-label');
      let pct = 0;
      const interval = setInterval(() => {
        pct = Math.min(pct + Math.random() * 8, 92);
        if (fill) fill.style.width = pct + '%';
        if (label) label.textContent = `Uploading… ${Math.round(pct)}%`;
        if (pct >= 92) clearInterval(interval);
      }, 400);
    }
    const submitBtn = uploadForm.querySelector('[type=submit]');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Uploading…'; }
  });
}

// ───────────────────────────────────────────────
// Admin: confirm destructive actions
// ───────────────────────────────────────────────
document.querySelectorAll('.confirm-action').forEach(form => {
  form.addEventListener('submit', e => {
    const msg = form.dataset.confirm || 'Are you sure?';
    if (!confirm(msg)) e.preventDefault();
  });
});

// ───────────────────────────────────────────────
// Toast notification
// ───────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const container = document.querySelector('.flash-container') || (() => {
    const c = document.createElement('div');
    c.className = 'flash-container';
    document.body.appendChild(c);
    return c;
  })();
  const el = document.createElement('div');
  el.className = `alert alert-${type}`;
  el.innerHTML = `<span>${escHtml(msg)}</span><button class="alert-close" onclick="this.parentElement.remove()">✕</button>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ───────────────────────────────────────────────
// Utilities
// ───────────────────────────────────────────────
function fmtCount(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
  return String(n);
}

function fmtSize(bytes) {
  if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB';
  if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return bytes + ' B';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Expose for inline onclick handlers
window.toggleReplyForm = toggleReplyForm;
window.deleteComment = deleteComment;
window.openReport = openReport;
window.closeReport = closeReport;
