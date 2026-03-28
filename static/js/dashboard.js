/* ═══════════════════════════════════════════════════════════════
   NOTES APP — Main Controller
═══════════════════════════════════════════════════════════════ */

let activeTagId = 'all';
let activeNoteId = null;
let autosaveTimer = null;
let searchQuery = '';

// ── Boot ──────────────────────────────────────────────────────

async function boot() {
  // Restore user avatar
  const user = JSON.parse(localStorage.getItem('mnemo_user') || '{}');
  if (user.username) {
    document.getElementById('topbar-avatar').textContent =
      user.username.slice(0, 2).toUpperCase();
  }

  if (isOnline) {
    await refreshNotesFromServer();
  } else {
    renderTagNav();
    renderNoteList();
  }

  updateOfflineQueueBadge();
}

boot();

// ── Rendering ─────────────────────────────────────────────────

function renderTagNav() {
  const tags = localDB.getTags();
  const notes = localDB.getNotes();
  const nav = document.getElementById('tag-nav');

  document.getElementById('all-count').textContent = notes.length;

  // Remove old tag items (keep "all")
  nav.querySelectorAll('.tag-item:not([data-tag-id="all"])').forEach(el => el.remove());

  tags.forEach(tag => {
    const noteCount = notes.filter(n => n.tag === tag.id || n.tag_id === tag.id).length;
    const item = document.createElement('div');
    item.className = 'tag-item' + (tag.id === activeTagId ? ' active' : '');
    item.dataset.tagId = tag.id;
    item.innerHTML = `
      <span class="tag-dot" style="background:${tag.color || 'var(--mist)'}"></span>
      <span style="flex:1">${escHtml(tag.name)}</span>
      <span class="tag-count">${noteCount}</span>
      <div class="tag-actions">
        <button class="tag-btn" title="Edit" onclick="event.stopPropagation();editTag('${tag.id}')">✎</button>
        <button class="tag-btn" title="Delete" onclick="event.stopPropagation();deleteTag('${tag.id}')">✕</button>
      </div>
    `;
    item.addEventListener('click', () => selectTag(tag.id, item));
    nav.appendChild(item);
  });
}

function renderNoteList() {
  const body = document.getElementById('note-list-body');
  let notes = localDB.getNotes();
  const queue = localDB.getQueue();
  const pendingIds = new Set(queue.map(q => q.id));

  // Filter by tag
  if (activeTagId !== 'all') {
    notes = notes.filter(n => (n.tag === activeTagId || n.tag_id === activeTagId || n.tag?.id === activeTagId));
  }

  // Filter by search
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    notes = notes.filter(n =>
      n.title?.toLowerCase().includes(q) ||
      n.content?.toLowerCase().includes(q)
    );
  }

  if (!notes.length) {
    body.innerHTML = `
      <div class="note-empty">
        <div class="note-empty-icon">✦</div>
        <div class="note-empty-text">${searchQuery ? 'No results' : 'No notes yet'}</div>
      </div>`;
    return;
  }

  const tags = localDB.getTags();
  const tagMap = Object.fromEntries(tags.map(t => [t.id, t]));

  body.innerHTML = notes.map(note => {
    const tagId = note.tag?.id || note.tag_id || note.tag;
    const tag = tagMap[tagId];
    const isPending = pendingIds.has(note.id);
    const preview = (note.content || '').replace(/\n/g, ' ').slice(0, 80);
    const date = formatDate(note.updated_at || note.created_at);
    return `
      <div class="note-card${note.id === activeNoteId ? ' active' : ''}${isPending ? ' offline-pending' : ''}"
        data-note-id="${note.id}"
        onclick="openNote('${note.id}')">
        <div class="note-card-tag" style="color:${tag?.color || 'var(--mist)'}">
          ${tag ? escHtml(tag.name) : '—'}
        </div>
        <div class="note-card-title">${escHtml(note.title || 'Untitled')}</div>
        <div class="note-card-preview">${escHtml(preview) || 'Empty note'}</div>
        <div class="note-card-meta">
          <span class="note-card-date">${date}</span>
        </div>
      </div>`;
  }).join('');
}

// ── Note CRUD ─────────────────────────────────────────────────

function openNote(id) {
  const notes = localDB.getNotes();
  const note = notes.find(n => n.id === id);
  if (!note) return;

  activeNoteId = id;

  // Highlight in list
  document.querySelectorAll('.note-card').forEach(c => {
    c.classList.toggle('active', c.dataset.noteId === id);
  });

  // Populate editor
  const tags = localDB.getTags();
  const tagId = note.tag?.id || note.tag_id || note.tag;
  const tag = tags.find(t => t.id === tagId);

  document.getElementById('editor-tag-label').textContent = tag ? tag.name : '—';
  document.getElementById('editor-tag-label').style.borderColor = tag?.color || 'var(--ink-4)';
  document.getElementById('editor-title').value = note.title || '';
  document.getElementById('editor-content').value = note.content || '';
  updateWordCount();

  document.getElementById('welcome-screen').style.display = 'none';
  const container = document.getElementById('editor-container');
  container.style.display = 'flex';
  container.style.flexDirection = 'column';
  container.style.overflow = 'hidden';

  document.getElementById('editor-content').focus();
}

function openNewNote() {
  const tags = localDB.getTags();
  if (!tags.length) {
    showToast('Create a tag first', 'warning');
    openTagModal('create');
    return;
  }

  const tag = tags[0];
  const tempId = 'local_' + Date.now();
  const note = {
    id: tempId,
    title: '',
    content: '',
    tag_id: tag.id,
    tag: tag.id,
    _synced: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  localDB.upsertNote(note);
  renderNoteList();
  openNote(tempId);

  document.getElementById('editor-title').focus();
}

async function saveCurrentNote() {
  if (!activeNoteId) return;
  const notes = localDB.getNotes();
  const note = notes.find(n => n.id === activeNoteId);
  if (!note) return;

  const title   = document.getElementById('editor-title').value;
  const content = document.getElementById('editor-content').value;
  const tagId   = note.tag_id || note.tag?.id || note.tag;

  const updated = { ...note, title, content, updated_at: new Date().toISOString() };
  localDB.upsertNote(updated);
  renderNoteList();

  // Show saving state
  const btn = document.getElementById('save-btn');
  const btnText = document.getElementById('save-btn-text');
  btn.disabled = true;
  btnText.textContent = 'Saving…';

  if (isOnline) {
    try {
      const isLocal = String(activeNoteId).startsWith('local_');
      if (isLocal) {
        const data = { title, content, tag_id: tagId };
        const created = await api('POST', '/v1/notes/', data);
        // Replace local ID
        localDB.deleteNote(activeNoteId);
        localDB.upsertNote({ ...created, _synced: true });
        activeNoteId = created.id;
        renderNoteList();
      } else {
        await api('PATCH', `/notes/${activeNoteId}/`, { title, content });
        localDB.upsertNote({ ...updated, _synced: true });
      }
      flashAutosave();
    } catch (e) {
      localDB.enqueue({
        type: String(activeNoteId).startsWith('local_') ? 'create_note' : 'update_note',
        id: activeNoteId,
        data: { title, content, tag_id: tagId }
      });
      showToast('Saved locally', 'warning');
    }
  } else {
    localDB.enqueue({
      type: String(activeNoteId).startsWith('local_') ? 'create_note' : 'update_note',
      id: activeNoteId,
      data: { title, content, tag_id: tagId }
    });
    showToast('Offline — saved locally', 'warning');
  }

  btn.disabled = false;
  btnText.textContent = 'Save';
}

async function deleteCurrentNote() {
  if (!activeNoteId) return;
  if (!confirm('Delete this note?')) return;

  const id = activeNoteId;
  localDB.deleteNote(id);

  if (isOnline && !String(id).startsWith('local_')) {
   try {
  await api('DELETE', `/v1/notes/${id}/`);
} catch (e) {
  if (e.status === 404) {
    // Already deleted on server → remove from queue if exists
    localDB.dequeue(id);
  } else {
    localDB.enqueue({ type: 'delete_note', id });
  }
}
  } else if (!String(id).startsWith('local_')) {
    localDB.enqueue({ type: 'delete_note', id });
  }

  activeNoteId = null;
  document.getElementById('welcome-screen').style.display = 'flex';
  document.getElementById('editor-container').style.display = 'none';
  renderNoteList();
  showToast('Note deleted', 'success');
}

// ── Autosave ──────────────────────────────────────────────────

function scheduleAutosave() {
  if (autosaveTimer) clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => {
    if (!activeNoteId) return;
    const title   = document.getElementById('editor-title').value;
    const content = document.getElementById('editor-content').value;
    const notes = localDB.getNotes();
    const note = notes.find(n => n.id === activeNoteId);
    if (note) {
      localDB.upsertNote({ ...note, title, content, updated_at: new Date().toISOString() });
      renderNoteList();
    }
    // Silent auto-save to server if online
    if (isOnline && !String(activeNoteId).startsWith('local_')) {
      api('PATCH', `/v1/notes/${activeNoteId}/`, { title, content })
        .then(() => flashAutosave())
        .catch(() => {});
    }
  }, 1500);
}

function flashAutosave() {
  const el = document.getElementById('autosave-indicator');
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), 2000);
}

// ── Tag ops ───────────────────────────────────────────────────

function selectTag(tagId, el) {
  activeTagId = tagId;
  document.querySelectorAll('.tag-item').forEach(i => i.classList.remove('active'));
  el.classList.add('active');

  const tags = localDB.getTags();
  const tag = tags.find(t => t.id === tagId);
  document.getElementById('note-list-title').textContent =
    tagId === 'all' ? 'All Notes' : (tag?.name || 'Notes');

  renderNoteList();
}

function filterTags(query) {
  const q = query.toLowerCase();
  document.querySelectorAll('#tag-nav .tag-item:not([data-tag-id="all"])').forEach(item => {
    item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

function editTag(id) {
  const tags = localDB.getTags();
  const tag = tags.find(t => t.id === id);
  if (tag) openTagModal('edit', tag);
}

async function deleteTag(id) {
  if (!confirm('Delete this tag? Notes using it will lose their tag.')) return;
  localDB.deleteTag(id);
  if (isOnline && !String(id).startsWith('local_')) {
    try { await api('DELETE', `/v1/tags/${id}/`); }
    catch (_) { localDB.enqueue({ type: 'delete_tag', id }); }
  } else {
    localDB.enqueue({ type: 'delete_tag', id });
  }
  if (activeTagId === id) activeTagId = 'all';
  renderTagNav();
  renderNoteList();
  showToast('Tag deleted', 'success');
}

function openChangeTag() {
  const tags = localDB.getTags();
  const list = document.getElementById('change-tag-list');
  list.innerHTML = tags.map(tag => `
    <div style="display:flex;align-items:center;gap:8px;padding:8px 10px;
      border-radius:4px;cursor:pointer;transition:background 0.15s;"
      onmouseover="this.style.background='var(--ink-3)'"
      onmouseout="this.style.background=''"
      onclick="changeNoteTag('${tag.id}','${escHtml(tag.name)}','${tag.color || '#888'}')">
      <span style="width:8px;height:8px;border-radius:2px;background:${tag.color || 'var(--mist)'}"></span>
      <span style="font-size:0.82rem">${escHtml(tag.name)}</span>
    </div>
  `).join('');
  document.getElementById('change-tag-modal').classList.add('open');
}

function changeNoteTag(tagId, tagName, tagColor) {
  if (!activeNoteId) return;
  const notes = localDB.getNotes();
  const note = notes.find(n => n.id === activeNoteId);
  if (!note) return;
  note.tag = tagId; note.tag_id = tagId;
  localDB.upsertNote(note);
  document.getElementById('editor-tag-label').textContent = tagName;
  document.getElementById('editor-tag-label').style.borderColor = tagColor;
  document.getElementById('change-tag-modal').classList.remove('open');
  renderNoteList();
  if (isOnline && !String(activeNoteId).startsWith('local_')) {
    api('PATCH', `/v1/notes/${activeNoteId}/`, { tag_id: tagId }).catch(() => {});
  }
}

// Close change-tag modal on backdrop
document.getElementById('change-tag-modal').addEventListener('click', function(e) {
  if (e.target === this) this.classList.remove('open');
});

// ── Search ────────────────────────────────────────────────────

function searchNotes(query) {
  searchQuery = query;
  renderNoteList();
}

function focusSearch() {
  document.getElementById('note-search').focus();
}

// ── Keyboard shortcuts ────────────────────────────────────────

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault();
    saveCurrentNote();
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
    e.preventDefault();
    openNewNote();
  }
  if (e.key === 'Escape') {
    closeTagModal();
    document.getElementById('change-tag-modal').classList.remove('open');
  }
});

// ── Logout ────────────────────────────────────────────────────

async function doLogout() {
  try {
    await api('POST', '/v1/auth/logout/');
  } catch (_) {}
  localStorage.removeItem('mnemo_user');
  localStorage.removeItem('mnemo_access');
  window.location.href = '/login/';
}

// ── Utility ───────────────────────────────────────────────────

function updateWordCount() {
  const text = document.getElementById('editor-content').value;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  document.getElementById('word-count').textContent = `${words} word${words !== 1 ? 's' : ''}`;
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff/86400)}d ago`;
  return d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
}

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}