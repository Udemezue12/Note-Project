/* ═══════════════════════════════════════════════════════════════
   MNEMO — Core Application Logic
   Offline-first note-taking with HTMX + localStorage sync
═══════════════════════════════════════════════════════════════ */

const DB_KEY = "mnemo_notes";
const TAG_KEY = "mnemo_tags";
const QUEUE_KEY = "mnemo_sync_queue";
const CSRF_KEY = "mnemo_csrf";

// ── Local DB ─────────────────────────────────────────────────

const localDB = {
  getNotes: () => JSON.parse(localStorage.getItem(DB_KEY) || "[]"),
  getTags: () => JSON.parse(localStorage.getItem(TAG_KEY) || "[]"),
  getQueue: () => JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]"),

  saveNotes: (notes) => localStorage.setItem(DB_KEY, JSON.stringify(notes)),
  saveTags: (tags) => localStorage.setItem(TAG_KEY, JSON.stringify(tags)),
  saveQueue: (q) => localStorage.setItem(QUEUE_KEY, JSON.stringify(q)),

  upsertNote(note) {
    const notes = this.getNotes();
    const idx = notes.findIndex((n) => n.id === note.id);
    if (idx >= 0) notes[idx] = { ...notes[idx], ...note };
    else notes.unshift(note);
    this.saveNotes(notes);
  },

  deleteNote(id) {
    const notes = this.getNotes().filter((n) => n.id !== id);
    this.saveNotes(notes);
  },

  upsertTag(tag) {
    const tags = this.getTags();
    const idx = tags.findIndex((t) => t.id === tag.id);
    if (idx >= 0) tags[idx] = { ...tags[idx], ...tag };
    else tags.unshift(tag);
    this.saveTags(tags);
  },

  deleteTag(id) {
    const tags = this.getTags().filter((t) => t.id !== id);
    this.saveTags(tags);
  },

  enqueue(action) {
    const q = this.getQueue();
    // Remove duplicate pending for same item
    const filtered = q.filter(
      (item) => !(item.type === action.type && item.id === action.id),
    );
    filtered.push({ ...action, queued_at: Date.now() });
    this.saveQueue(filtered);
    updateOfflineQueueBadge();
  },

  dequeue(id) {
    const q = this.getQueue().filter((item) => item.id !== id);
    this.saveQueue(q);
    updateOfflineQueueBadge();
  },
};

// ── Network State ─────────────────────────────────────────────

let isOnline = navigator.onLine;
let syncTimer = null;

function setOnlineStatus(online) {
  isOnline = online;
  const badge = document.getElementById("sync-status");
  if (!badge) return;
  badge.className = "sync-status " + (online ? "online" : "offline");
  badge.querySelector(".sync-label").textContent = online
    ? "online"
    : "offline";
  if (online) scheduleSync();
}

window.addEventListener("online", () => {
  setOnlineStatus(true);
  showToast("Back online — syncing…", "success");
});
window.addEventListener("offline", () => {
  setOnlineStatus(false);
  showToast("Offline — notes saved locally", "warning");
});

// ── CSRF ──────────────────────────────────────────────────────

function getCsrf() {
  // Try cookie first
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  if (match) return match[1];
  return localStorage.getItem(CSRF_KEY) || "";
}

// ── API Client ────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrf(),
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error(err.detail || "Request failed"), {
      status: res.status,
      data: err,
    });
  }
  return res.status === 204 ? null : res.json();
}

// ── Sync Engine ───────────────────────────────────────────────

async function syncQueue() {
  const queue = localDB.getQueue();
  if (!queue.length || !isOnline) return;

  setSyncingState(true);
  let synced = 0,
    failed = 0;

  for (const item of queue) {
    try {
      if (item.type === "create_note") {
        const { _local_id, ...payload } = item.data;
        const created = await api("POST", "/v1/notes/", payload);
        // Update local ID mapping
        const notes = localDB.getNotes();
        const idx = notes.findIndex((n) => n.id === item.id);
        if (idx >= 0) {
          notes[idx].id = created.id;
          notes[idx]._synced = true;
        }
        localDB.saveNotes(notes);
      } else if (item.type === "update_note") {
        await api("PATCH", `/v1/notes/${item.id}/`, item.data);
      } else if (item.type === "delete_note") {
        await api("DELETE", `/v1/notes/${item.id}/`);
      } else if (item.type === "create_tag") {
        const created = await api("POST", "/v1/tags/", item.data);
        const tags = localDB.getTags();
        const idx = tags.findIndex((t) => t.id === item.id);
        if (idx >= 0) {
          tags[idx].id = created.id;
          tags[idx]._synced = true;
        }
        localDB.saveTags(tags);
      } else if (item.type === "update_tag") {
        await api("PATCH", `/v1/tags/${item.id}/`, item.data);
      } else if (item.type === "delete_tag") {
        await api("DELETE", `/v1/tags/${item.id}/`);
      }

      localDB.dequeue(item.id);
      synced++;
    } catch (e) {
      console.warn("Sync failed for", item, e);
      failed++;
    }
  }

  // Call server sync endpoint if available
  try {
    await api("POST", "/v1/sync/", { client_time: Date.now() });
  } catch (_) {}

  setSyncingState(false);
  if (synced)
    showToast(`Synced ${synced} item${synced > 1 ? "s" : ""}`, "success");
  if (failed)
    showToast(`${failed} item${failed > 1 ? "s" : ""} failed to sync`, "error");

  // Re-render note list from fresh server data
  if (synced) await refreshNotesFromServer();
}

function scheduleSync() {
  if (syncTimer) clearTimeout(syncTimer);
  syncTimer = setTimeout(syncQueue, 800);
}

async function refreshNotesFromServer() {
  try {
    const [notes, tags] = await Promise.all([
      api("GET", "/v1/notes/"),
      api("GET", "/v1/tags/"),
    ]);
    localDB.saveNotes(notes.results || notes);
    localDB.saveTags(tags.results || tags);
    renderNoteList();
    renderTagNav();
  } catch (_) {}
}

function setSyncingState(syncing) {
  const badge = document.getElementById("sync-status");
  if (!badge) return;
  if (syncing) {
    badge.className = "sync-status syncing";
    badge.querySelector(".sync-label").textContent = "syncing…";
  } else {
    setOnlineStatus(isOnline);
  }
}

function updateOfflineQueueBadge() {
  const el = document.getElementById("offline-queue");
  if (!el) return;
  const count = localDB.getQueue().length;
  el.querySelector(".count").textContent = count;
  el.classList.toggle("visible", count > 0);
}

// ── Toast ─────────────────────────────────────────────────────

function showToast(msg, type = "info", duration = 3000) {
  const ct = document.getElementById("toast-container");
  if (!ct) return;
  const icon =
    { success: "✓", error: "✕", warning: "⚠", info: "ℹ" }[type] || "ℹ";
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${icon}</span><span>${msg}</span>`;
  ct.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    t.style.transform = "translateY(8px)";
    t.style.transition = "all 0.2s";
    setTimeout(() => t.remove(), 200);
  }, duration);
}

// ── Tag Modal ─────────────────────────────────────────────────

let tagModalMode = "create";
let tagModalEditId = null;
let selectedColor = "#4a7c59";

document.querySelectorAll(".color-swatch").forEach((sw) => {
  sw.addEventListener("click", () => {
    document
      .querySelectorAll(".color-swatch")
      .forEach((s) => s.classList.remove("selected"));
    sw.classList.add("selected");
    selectedColor = sw.dataset.color;
  });
});

function openTagModal(mode = "create", tag = null) {
  tagModalMode = mode;
  tagModalEditId = tag ? tag.id : null;
  const modal = document.getElementById("tag-modal");
  const title = document.getElementById("tag-modal-title");
  const nameInput = document.getElementById("tag-name-input");
  const saveBtn = document.getElementById("tag-modal-save");

  if (mode === "edit" && tag) {
    title.textContent = "Edit Tag";
    nameInput.value = tag.name;
    saveBtn.textContent = "Save Changes";
    // Select color
    selectedColor = tag.color || "#4a7c59";
    document.querySelectorAll(".color-swatch").forEach((s) => {
      s.classList.toggle("selected", s.dataset.color === selectedColor);
    });
  } else {
    title.textContent = "New Tag";
    nameInput.value = "";
    saveBtn.textContent = "Create Tag";
    selectedColor = "#4a7c59";
    document
      .querySelectorAll(".color-swatch")
      .forEach((s, i) => s.classList.toggle("selected", i === 0));
  }

  modal.classList.add("open");
  setTimeout(() => nameInput.focus(), 100);
}

function closeTagModal() {
  document.getElementById("tag-modal").classList.remove("open");
}

async function saveTag() {
  const name = document.getElementById("tag-name-input").value.trim();
  if (!name) {
    showToast("Tag name required", "error");
    return;
  }

  const tagData = { name, color: selectedColor };

  if (tagModalMode === "create") {
    const tempId = "local_" + Date.now();
    const tag = {
      id: tempId,
      ...tagData,
      _synced: false,
      created_at: new Date().toISOString(),
    };
    localDB.upsertTag(tag);

    if (isOnline) {
      try {
        const created = await api("POST", "/v1/tags/", tagData);
        tag.id = created.id;
        tag._synced = true;
        localDB.upsertTag(tag);
      } catch (e) {
        localDB.enqueue({ type: "create_tag", id: tempId, data: tagData });
        showToast("Tag saved locally", "warning");
      }
    } else {
      localDB.enqueue({ type: "create_tag", id: tempId, data: tagData });
      showToast("Tag saved — will sync when online", "warning");
    }
  } else {
    localDB.upsertTag({ id: tagModalEditId, ...tagData });
    if (isOnline) {
      try {
        await api("PATCH", `/v1/tags/${tagModalEditId}/`, tagData);
      } catch (_) {
        localDB.enqueue({
          type: "update_tag",
          id: tagModalEditId,
          data: tagData,
        });
      }
    } else {
      localDB.enqueue({
        type: "update_tag",
        id: tagModalEditId,
        data: tagData,
      });
    }
  }

  closeTagModal();
  renderTagNav();
  showToast(
    tagModalMode === "create" ? "Tag created" : "Tag updated",
    "success",
  );
}

// Close on backdrop click
document.getElementById("tag-modal").addEventListener("click", function (e) {
  if (e.target === this) closeTagModal();
});

// Init
setOnlineStatus(navigator.onLine);
if (isOnline) scheduleSync();
