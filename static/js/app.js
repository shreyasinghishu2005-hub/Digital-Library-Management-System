/**
 * Digital Library System - Frontend Application Logic
 * Client state management, REST API interactions, Chart.js integrations,
 * barcode simulation, and bilingual UI rendering.
 */

// Global Application State
const state = {
  user: null,
  token: localStorage.getItem("lms_token") || null,
  books: [],
  transactions: [],
  members: [],
  notifications: [],
  recommendations: [],
  analytics: null,
  language: localStorage.getItem("lms_lang") || "en",
  currentView: "auth",
  currentCategory: "all",
  availableOnly: false,
  viewMode: "grid", // 'grid' or 'table'
  charts: {
    mostBorrowed: null,
    categories: null,
    trends: null
  }
};

// ------------------ API CLIENT ------------------

const API_BASE = window.location.protocol === "file:" ? "http://localhost:8080" : "";

async function api(endpoint, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (state.token) {
    headers["X-Session-Token"] = state.token;
  }

  try {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
      ...options,
      headers
    });

    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || `HTTP error ${res.status}`);
      }
      return data;
    }

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP error ${res.status}`);
    }

    return await res.text();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

// ------------------ TOAST NOTIFICATIONS ------------------

function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const iconSvg = type === "success" 
    ? `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#047857" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`
    : type === "error"
    ? `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#B91C1C" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`
    : `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#2563EB" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;

  toast.innerHTML = `
    ${iconSvg}
    <span class="toast-msg">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

function showAlert(message, type = "success") {
  const alertBox = document.getElementById("alertBox");
  if (!alertBox) return;

  alertBox.className = `alert-banner ${type}`;
  alertBox.textContent = message;
  alertBox.classList.remove("hidden");

  setTimeout(() => {
    alertBox.classList.add("hidden");
  }, 5000);
}

// ------------------ TRANSLATIONS & I18N ------------------

function setLanguage(lang) {
  state.language = lang;
  localStorage.setItem("lms_lang", lang);

  const langSelect = document.getElementById("languageSelect");
  if (langSelect) langSelect.value = lang;

  const dict = translations[lang] || translations.en;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) {
      if (el.tagName === "INPUT" && el.placeholder) {
        el.placeholder = dict[key];
      } else {
        el.textContent = dict[key];
      }
    }
  });

  // Re-render dynamic elements with current language strings
  if (state.books.length > 0) renderBooks();
}

// ------------------ AUTH & SESSION ------------------

function setAuth(user, token) {
  state.user = user;
  state.token = token;
  localStorage.setItem("lms_token", token);
  applyAuthUI();
  switchView("dashboard");
  loadAllData();
  showToast(`Welcome back, ${user.name}!`, "success");
}

function clearAuth() {
  state.user = null;
  state.token = null;
  localStorage.removeItem("lms_token");
  applyAuthUI();
  switchView("auth");
  showToast("Logged out successfully.", "info");
}

function applyAuthUI() {
  const isAuthed = Boolean(state.user && state.token);
  const isAdmin = state.user?.role === "admin";

  // Elements visibility based on auth
  document.querySelectorAll("[data-auth='true']").forEach((el) => {
    el.classList.toggle("hidden", !isAuthed);
  });

  // Admin-only elements
  document.querySelectorAll(".admin-only").forEach((el) => {
    el.classList.toggle("hidden", !(isAuthed && isAdmin));
  });

  // Profile badge
  const profileBadge = document.getElementById("profileBadge");
  const userName = document.getElementById("userName");
  const userRole = document.getElementById("userRole");
  const userAvatar = document.getElementById("userAvatar");
  const notifBellWrapper = document.getElementById("notificationBellWrapper");
  const logoutBtn = document.getElementById("logoutBtn");
  const heroQuickIssueBtn = document.getElementById("heroQuickIssueBtn");

  if (isAuthed) {
    if (userName) userName.textContent = state.user.name;
    if (userRole) userRole.textContent = state.user.role.toUpperCase();
    if (userAvatar) userAvatar.textContent = state.user.name.charAt(0).toUpperCase();
    if (notifBellWrapper) notifBellWrapper.classList.remove("hidden");
    if (logoutBtn) logoutBtn.classList.remove("hidden");
    if (heroQuickIssueBtn) heroQuickIssueBtn.classList.remove("hidden");
  } else {
    if (userName) userName.textContent = "Guest";
    if (userRole) userRole.textContent = "Not logged in";
    if (userAvatar) userAvatar.textContent = "G";
    if (notifBellWrapper) notifBellWrapper.classList.add("hidden");
    if (logoutBtn) logoutBtn.classList.add("hidden");
    if (heroQuickIssueBtn) heroQuickIssueBtn.classList.add("hidden");
  }
}

async function checkSession() {
  if (!state.token) {
    applyAuthUI();
    return;
  }

  try {
    const data = await api("/session");
    if (data.success && data.user) {
      state.user = data.user;
      applyAuthUI();
      switchView("dashboard");
      loadAllData();
    } else {
      clearAuth();
    }
  } catch (err) {
    clearAuth();
  }
}

// ------------------ VIEW NAVIGATION ------------------

function switchView(viewName) {
  state.currentView = viewName;

  // Toggle active view panel
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.remove("active");
  });
  const targetPanel = document.getElementById(`view-${viewName}`);
  if (targetPanel) {
    targetPanel.classList.add("active");
  }

  // Toggle active nav menu button
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.remove("active");
    if (btn.dataset.view === viewName) {
      btn.classList.add("active");
    }
  });

  // Update topbar title
  const pageTitle = document.getElementById("pageTitle");
  const dict = translations[state.language] || translations.en;
  if (pageTitle) {
    const titleKey = {
      auth: "loginTitle",
      dashboard: "menuDashboard",
      books: "menuBooks",
      circulation: "menuIssue",
      "add-book": "addBookTitle",
      analytics: "menuAnalytics"
    }[viewName] || "menuDashboard";
    pageTitle.textContent = dict[titleKey] || viewName;
  }

  // Close mobile sidebar if open
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.remove("mobile-open");

  // Load view-specific data
  if (viewName === "dashboard") {
    loadDashboardStats();
    loadNotifications();
    loadRecommendations();
  } else if (viewName === "books") {
    loadBooks();
  } else if (viewName === "circulation") {
    loadCirculationData();
  } else if (viewName === "analytics" && state.user?.role === "admin") {
    loadAnalytics();
  }
}

// ------------------ DATA LOADING ------------------

async function loadAllData() {
  await Promise.all([
    loadDashboardStats(),
    loadBooks(),
    loadCirculationData(),
    loadNotifications(),
    loadRecommendations()
  ]);
  if (state.user?.role === "admin") {
    loadAnalytics();
    loadMembers();
  }
}

async function loadDashboardStats() {
  if (!state.token) return;
  try {
    const data = await api("/dashboard");
    if (data.success) {
      renderStats(data.dashboard);
    }
  } catch (err) {
    console.error("Failed to load dashboard stats:", err);
  }
}

async function loadBooks() {
  try {
    const params = new URLSearchParams();
    const searchVal = document.getElementById("bookSearchInput")?.value || "";
    if (searchVal) params.set("search", searchVal);
    if (state.currentCategory && state.currentCategory !== "all") {
      params.set("category", state.currentCategory);
    }
    if (state.availableOnly) params.set("available_only", "true");

    const data = await api(`/books?${params.toString()}`);
    if (data.success) {
      state.books = data.books;
      renderBooks();
      renderCategoryChips();
      populateIssueBookDropdown();
    }
  } catch (err) {
    console.error("Failed to load books:", err);
  }
}

async function loadCirculationData() {
  if (!state.token) return;
  try {
    const data = await api("/transactions");
    if (data.success) {
      state.transactions = data.transactions;
      renderTransactions();
      renderDashboardRecentTable();
    }
  } catch (err) {
    console.error("Failed to load transactions:", err);
  }
}

async function loadNotifications() {
  if (!state.token) return;
  try {
    const data = await api("/notifications");
    if (data.success) {
      state.notifications = data.notifications;
      renderNotifications();
    }
  } catch (err) {
    console.error("Failed to load notifications:", err);
  }
}

async function loadRecommendations() {
  if (!state.token) return;
  try {
    const data = await api("/recommendations");
    if (data.success) {
      state.recommendations = data.recommendations;
      renderRecommendations();
    }
  } catch (err) {
    console.error("Failed to load recommendations:", err);
  }
}

async function loadMembers() {
  if (state.user?.role !== "admin") return;
  try {
    const data = await api("/users");
    if (data.success) {
      state.members = data.users;
      populateMemberDropdown();
    }
  } catch (err) {
    console.error("Failed to load users:", err);
  }
}

async function loadAnalytics() {
  if (state.user?.role !== "admin") return;
  try {
    const data = await api("/analytics");
    if (data.success) {
      state.analytics = data.analytics;
      renderAnalyticsCharts(data.analytics);
    }
  } catch (err) {
    console.error("Failed to load analytics:", err);
  }
}

// ------------------ RENDERING FUNCTIONS ------------------

function renderStats(stats) {
  const statsGrid = document.getElementById("statsGrid");
  if (!statsGrid) return;

  const isAdmin = state.user?.role === "admin";
  let cardsHtml = "";

  if (isAdmin) {
    cardsHtml = `
      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </div>
          <span class="metric-tag status-badge available">Catalog</span>
        </div>
        <div class="metric-value">${stats.total_books || 0}</div>
        <div class="metric-label">Total Unique Titles (${stats.total_copies || 0} copies)</div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap" style="color: #2563EB; background: #EFF6FF;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
          <span class="metric-tag status-badge issued">Active</span>
        </div>
        <div class="metric-value">${stats.active_issues || 0}</div>
        <div class="metric-label">Currently Issued Books</div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap" style="color: #DC2626; background: #FEF2F2;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <span class="metric-tag status-badge out-of-stock">Overdue</span>
        </div>
        <div class="metric-value">${stats.overdue_issues || 0}</div>
        <div class="metric-label">Overdue Loans Requiring Action</div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap" style="color: #059669; background: #ECFDF5;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          </div>
          <span class="metric-tag status-badge available">Revenue</span>
        </div>
        <div class="metric-value">₹${(stats.total_fines_collected || 0).toFixed(2)}</div>
        <div class="metric-label">Total Overdue Fines Collected</div>
      </div>
    `;
  } else {
    cardsHtml = `
      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap" style="color: #2563EB; background: #EFF6FF;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </div>
          <span class="metric-tag status-badge issued">Loans</span>
        </div>
        <div class="metric-value">${stats.my_issued_books || 0}</div>
        <div class="metric-label">My Current Active Loans</div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap" style="color: #059669; background: #ECFDF5;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <span class="metric-tag status-badge available">Returned</span>
        </div>
        <div class="metric-value">${stats.my_returned_books || 0}</div>
        <div class="metric-label">Books Completed & Returned</div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap" style="color: #DC2626; background: #FEF2F2;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <span class="metric-tag status-badge out-of-stock">Overdue</span>
        </div>
        <div class="metric-value">${stats.my_overdue_books || 0}</div>
        <div class="metric-label">Overdue Books with Late Fines</div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          </div>
          <span class="metric-tag status-badge available">Dues</span>
        </div>
        <div class="metric-value">₹${(stats.my_unpaid_fines || 0).toFixed(2)}</div>
        <div class="metric-label">My Outstanding Fines Due</div>
      </div>
    `;
  }

  statsGrid.innerHTML = cardsHtml;
}

function renderNotifications() {
  const notifList = document.getElementById("notificationsList");
  const drawerList = document.getElementById("drawerNotificationsList");
  const countBadge = document.getElementById("notificationCount");

  const count = state.notifications.length;
  if (countBadge) {
    countBadge.textContent = count;
    countBadge.classList.toggle("hidden", count === 0);
  }

  let html = "";
  if (count === 0) {
    html = `<p class="text-xs text-muted" style="padding: 16px; text-align: center;">No active notices or overdue fines at this time.</p>`;
  } else {
    html = state.notifications.map((n) => `
      <div class="notif-item ${n.type}">
        <div class="notif-content">
          <h4 class="notif-title">${n.title}</h4>
          <p class="notif-msg">${n.message}</p>
          ${n.transaction_id ? `
            <button class="notif-action-btn" onclick="openPaymentModal(${n.transaction_id}, 0, '${escapeHtml(n.title)}')">
              Settle Fine Online &rarr;
            </button>
          ` : ""}
        </div>
      </div>
    `).join("");
  }

  if (notifList) notifList.innerHTML = html;
  if (drawerList) drawerList.innerHTML = html;
}

function renderRecommendations() {
  const recList = document.getElementById("recommendationsList");
  if (!recList) return;

  if (state.recommendations.length === 0) {
    recList.innerHTML = `<p class="text-xs text-muted" style="padding: 16px;">No recommendations available yet. Browse catalog to start reading!</p>`;
    return;
  }

  recList.innerHTML = state.recommendations.map((b) => `
    <div class="rec-card">
      <div>
        <div class="rec-category">${escapeHtml(b.category)}</div>
        <h4 class="rec-title">${escapeHtml(b.title)}</h4>
        <p class="rec-author">by ${escapeHtml(b.author)}</p>
      </div>
      <div class="rec-footer">
        <span class="status-badge ${b.available_copies > 0 ? "available" : "out-of-stock"}">
          ${b.available_copies > 0 ? `${b.available_copies} Available` : "Out of Stock"}
        </span>
        <button class="btn-text-action" onclick="quickIssueBook(${b.id})">Issue &rarr;</button>
      </div>
    </div>
  `).join("");
}

function renderBooks() {
  const grid = document.getElementById("booksGrid");
  const tableBody = document.getElementById("booksTableBody");
  const countLabel = document.getElementById("booksResultsCount");

  if (countLabel) {
    countLabel.textContent = `Showing ${state.books.length} book(s)`;
  }

  const isAdmin = state.user?.role === "admin";

  // Grid View
  if (grid) {
    if (state.books.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; padding: 48px; text-align: center; color: var(--text-muted);">No books match your criteria. Try adjusting your search or filters.</div>`;
    } else {
      grid.innerHTML = state.books.map((b) => {
        const isAvailable = b.available_copies > 0;
        const percent = Math.round((b.available_copies / b.total_copies) * 100);

        return `
          <div class="book-card" id="book-card-${b.id}">
            <div>
              <div class="book-card-top">
                <span class="book-category-pill">${escapeHtml(b.category)}</span>
                <span class="status-badge ${isAvailable ? "available" : "out-of-stock"}">
                  ${isAvailable ? "Available" : "All Issued"}
                </span>
              </div>
              <h3 class="book-title" title="${escapeHtml(b.title)}">${escapeHtml(b.title)}</h3>
              <p class="book-author">by ${escapeHtml(b.author)}</p>
              <p class="book-desc-clamp">${escapeHtml(b.description || "No description provided.")}</p>

              <div class="book-meta-row">
                <span>ISBN: ${escapeHtml(b.isbn)}</span>
                <span class="book-barcode-pill" onclick="simulateBarcodeLookup('${b.barcode}')" title="Click to view barcode">${escapeHtml(b.barcode)}</span>
              </div>

              <div class="copies-bar-container">
                <div class="copies-label-row">
                  <span>Available Copies</span>
                  <span><strong>${b.available_copies}</strong> of ${b.total_copies}</span>
                </div>
                <div class="copies-progress">
                  <div class="copies-progress-fill" style="width: ${percent}%;"></div>
                </div>
              </div>
            </div>

            <div class="book-card-actions">
              <button class="btn-card-issue" onclick="quickIssueBook(${b.id})" ${!isAvailable ? "disabled" : ""}>
                ${isAvailable ? "Issue Book" : "Unavailable"}
              </button>
              ${isAdmin ? `
                <button class="btn-card-icon" title="Edit Book" onclick="openEditBookModal(${b.id})">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button class="btn-card-icon" title="Delete Book" onclick="deleteBook(${b.id})">
                  <svg viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              ` : ""}
            </div>
          </div>
        `;
      }).join("");
    }
  }

  // Table View
  if (tableBody) {
    tableBody.innerHTML = state.books.map((b) => `
      <tr>
        <td>
          <strong>${escapeHtml(b.title)}</strong><br>
          <span class="text-xs text-muted">${escapeHtml(b.author)}</span>
        </td>
        <td><span class="book-category-pill">${escapeHtml(b.category)}</span></td>
        <td class="font-mono text-xs">${escapeHtml(b.isbn)}</td>
        <td class="font-mono text-xs"><span class="book-barcode-pill">${escapeHtml(b.barcode)}</span></td>
        <td>
          <span class="status-badge ${b.available_copies > 0 ? "available" : "out-of-stock"}">
            ${b.available_copies} / ${b.total_copies}
          </span>
        </td>
        <td>
          <button class="btn-secondary-white" onclick="quickIssueBook(${b.id})" ${b.available_copies <= 0 ? "disabled" : ""}>
            Issue
          </button>
        </td>
      </tr>
    `).join("");
  }
}

function renderCategoryChips() {
  const container = document.getElementById("categoryChips");
  if (!container) return;

  const categories = ["all", ...new Set(state.books.map((b) => b.category))];
  container.innerHTML = categories.map((cat) => `
    <button class="chip ${state.currentCategory === cat ? "active" : ""}" data-category="${cat}">
      ${cat === "all" ? "All Books" : escapeHtml(cat)}
    </button>
  `).join("");

  container.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.currentCategory = btn.dataset.category;
      loadBooks();
    });
  });
}

function renderTransactions(filter = "all") {
  const tbody = document.getElementById("transactionsBody");
  if (!tbody) return;

  let items = state.transactions;
  if (filter === "issued") {
    items = items.filter((t) => t.status === "issued" && !t.is_overdue);
  } else if (filter === "overdue") {
    items = items.filter((t) => t.is_overdue || (t.status === "returned" && t.fine_amount > 0 && !t.fine_paid));
  } else if (filter === "returned") {
    items = items.filter((t) => t.status === "returned");
  }

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 32px; color: var(--text-muted);">No transaction records found under this filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map((t) => {
    const isIssued = t.status === "issued";
    const hasFine = t.fine_amount > 0;
    const isPaid = Boolean(t.fine_paid);

    return `
      <tr>
        <td class="font-mono text-xs">#${t.id}</td>
        <td>
          <strong>${escapeHtml(t.book_title)}</strong><br>
          <span class="text-xs text-muted">${escapeHtml(t.book_barcode)}</span>
        </td>
        <td>
          ${escapeHtml(t.user_name)}<br>
          <span class="text-xs text-muted">${escapeHtml(t.user_email || "")}</span>
        </td>
        <td class="text-xs">${t.issue_date}</td>
        <td class="text-xs ${t.is_overdue ? "text-danger" : ""}">
          <strong>${t.due_date}</strong>
          ${t.is_overdue ? '<br><span class="status-badge out-of-stock" style="font-size: 0.68rem;">OVERDUE</span>' : ""}
        </td>
        <td class="text-xs">${t.return_date || "—"}</td>
        <td>
          <span class="status-badge ${isIssued ? (t.is_overdue ? "out-of-stock" : "issued") : "returned"}">
            ${isIssued ? (t.is_overdue ? "Overdue Loan" : "Issued") : "Returned"}
          </span>
        </td>
        <td>
          ${hasFine ? `
            <span style="color: ${isPaid ? "#047857" : "#B91C1C"}; font-weight: 700;">
              ₹${t.fine_amount.toFixed(2)}
            </span>
            <span class="status-badge ${isPaid ? "available" : "out-of-stock"}" style="font-size: 0.65rem; margin-left: 4px;">
              ${isPaid ? "PAID" : "UNPAID"}
            </span>
          ` : '<span class="text-muted">₹0.00</span>'}
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            ${isIssued ? `
              <button class="btn-secondary-white" onclick="processReturnBook(${t.id})">Return</button>
            ` : ""}
            ${hasFine && !isPaid ? `
              <button class="btn-card-issue" style="padding: 6px 10px; font-size: 0.78rem;" onclick="openPaymentModal(${t.id}, ${t.fine_amount}, '${escapeHtml(t.book_title)}')">
                Pay Fine
              </button>
            ` : ""}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function renderDashboardRecentTable() {
  const tbody = document.getElementById("dashboardRecentBody");
  if (!tbody) return;

  const recents = state.transactions.slice(0, 5);
  if (recents.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px; color: var(--text-muted);">No recent circulation activity.</td></tr>`;
    return;
  }

  tbody.innerHTML = recents.map((t) => `
    <tr>
      <td><strong>${escapeHtml(t.book_title)}</strong></td>
      <td>${escapeHtml(t.user_name)}</td>
      <td class="text-xs">${t.issue_date}</td>
      <td class="text-xs">${t.due_date}</td>
      <td>
        <span class="status-badge ${t.status === "issued" ? (t.is_overdue ? "out-of-stock" : "issued") : "returned"}">
          ${t.status.toUpperCase()}
        </span>
      </td>
      <td>
        ${t.fine_amount > 0 ? `<strong style="color: #B91C1C;">₹${t.fine_amount.toFixed(2)}</strong>` : "₹0.00"}
      </td>
    </tr>
  `).join("");
}

function renderAnalyticsCharts(analytics) {
  if (typeof Chart === "undefined") return;

  // Chart 1: Most Borrowed Books
  const ctxBorrowed = document.getElementById("chartMostBorrowedCanvas");
  if (ctxBorrowed && analytics.most_borrowed_books) {
    if (state.charts.mostBorrowed) state.charts.mostBorrowed.destroy();

    const labels = analytics.most_borrowed_books.map((b) => b.label);
    const data = analytics.most_borrowed_books.map((b) => b.value);

    state.charts.mostBorrowed = new Chart(ctxBorrowed, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Times Borrowed",
          data,
          backgroundColor: "#2563EB",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // Chart 2: Category Distribution
  const ctxCat = document.getElementById("chartCategoryCanvas");
  if (ctxCat && analytics.categories) {
    if (state.charts.categories) state.charts.categories.destroy();

    const labels = analytics.categories.map((c) => c.label);
    const data = analytics.categories.map((c) => c.value);

    state.charts.categories = new Chart(ctxCat, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: ["#2563EB", "#059669", "#D97706", "#7C3AED", "#DB2777", "#475569"],
          borderWidth: 2,
          borderColor: "#FFFFFF"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" }
        }
      }
    });
  }

  // Chart 3: Monthly Trends
  const ctxTrends = document.getElementById("chartTrendsCanvas");
  if (ctxTrends && analytics.monthly_trends) {
    if (state.charts.trends) state.charts.trends.destroy();

    const labels = analytics.monthly_trends.map((t) => t.label);
    const data = analytics.monthly_trends.map((t) => t.value);

    state.charts.trends = new Chart(ctxTrends, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Books Borrowed",
          data,
          borderColor: "#0F172A",
          backgroundColor: "rgba(15, 23, 42, 0.04)",
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointBackgroundColor: "#2563EB"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
          x: { grid: { display: false } }
        }
      }
    });
  }
}

function populateIssueBookDropdown() {
  const select = document.getElementById("issueBookSelect");
  if (!select) return;

  const currentVal = select.value;
  select.innerHTML = `<option value="">-- Choose an Available Book --</option>` +
    state.books
      .filter((b) => b.available_copies > 0)
      .map((b) => `<option value="${b.id}">${escapeHtml(b.title)} (${b.available_copies} avail) [${b.barcode}]</option>`)
      .join("");

  if (currentVal) select.value = currentVal;
}

function populateMemberDropdown() {
  const select = document.getElementById("issueUserSelect");
  if (!select) return;

  select.innerHTML = state.members.map((u) => `
    <option value="${u.id}">${escapeHtml(u.name)} (${escapeHtml(u.email)}) - ${u.role.toUpperCase()}</option>
  `).join("");
}

// ------------------ BOOK CIRCULATION ACTIONS ------------------

function quickIssueBook(bookId) {
  if (!state.token) {
    switchView("auth");
    showToast("Please sign in or select a demo account to issue books.", "info");
    return;
  }
  switchView("circulation");
  const select = document.getElementById("issueBookSelect");
  if (select) {
    select.value = bookId;
    select.scrollIntoView({ behavior: "smooth", block: "center" });
    select.focus();
  }
}

async function processReturnBook(txId) {
  if (!confirm("Are you sure you want to mark this book as returned?")) return;

  try {
    const data = await api("/return-book", {
      method: "POST",
      body: JSON.stringify({ transaction_id: txId })
    });

    if (data.success) {
      showToast(data.message, "success");
      await loadAllData();
      if (data.return_info?.fine_amount > 0) {
        openPaymentModal(txId, data.return_info.fine_amount, data.return_info.book_title);
      }
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteBook(bookId) {
  if (!confirm("Are you sure you want to delete this book from the library catalog?")) return;

  try {
    const data = await api(`/books/${bookId}`, { method: "DELETE" });
    if (data.success) {
      showToast(data.message, "success");
      loadBooks();
      loadDashboardStats();
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ------------------ MODAL CONTROLS ------------------

function openPaymentModal(txId, amount, bookTitle) {
  const modal = document.getElementById("paymentModal");
  const amountEl = document.getElementById("modalFineAmount");
  const detailsEl = document.getElementById("modalFineDetails");
  const txIdInput = document.getElementById("payModalTxId");

  if (!modal) return;
  txIdInput.value = txId;
  amountEl.textContent = `₹${parseFloat(amount || 0).toFixed(2)}`;
  detailsEl.textContent = `For: ${bookTitle || "Library Book Loan"}`;

  modal.classList.remove("hidden");
}

function openEditBookModal(bookId) {
  const book = state.books.find((b) => b.id === bookId);
  if (!book) return;

  document.getElementById("editBookId").value = book.id;
  document.getElementById("editTitle").value = book.title;
  document.getElementById("editAuthor").value = book.author;
  document.getElementById("editCategory").value = book.category;
  document.getElementById("editIsbn").value = book.isbn;
  document.getElementById("editBarcode").value = book.barcode;
  document.getElementById("editTotalCopies").value = book.total_copies;
  document.getElementById("editDescription").value = book.description || "";

  document.getElementById("editBookModal")?.classList.remove("hidden");
}

function simulateBarcodeLookup(code) {
  const modal = document.getElementById("barcodeModal");
  const input = document.getElementById("barcodeInput");
  if (modal) modal.classList.remove("hidden");
  if (input) {
    input.value = code;
    renderBarcodeSvg(code);
    performBarcodeSearch(code);
  }
}

function renderBarcodeSvg(code) {
  const svg = document.getElementById("barcodeSvgGraphic");
  const str = document.getElementById("barcodeDisplayString");
  if (str) str.textContent = code;
  if (!svg) return;

  // Generate authentic barcode bars
  let bars = "";
  let x = 10;
  for (let i = 0; i < code.length; i++) {
    const charCode = code.charCodeAt(i);
    const w1 = (charCode % 3) + 1.5;
    const w2 = ((charCode * 2) % 4) + 1;
    bars += `<rect x="${x}" y="5" width="${w1}" height="45" fill="#0F172A" />`;
    x += w1 + 2;
    bars += `<rect x="${x}" y="5" width="${w2}" height="45" fill="#0F172A" />`;
    x += w2 + 3;
  }
  svg.innerHTML = bars;
}

function performBarcodeSearch(code) {
  const resultBox = document.getElementById("barcodeLookupResult");
  if (!resultBox) return;

  const found = state.books.find((b) => b.barcode.toUpperCase() === code.trim().toUpperCase());
  if (found) {
    resultBox.classList.remove("hidden");
    resultBox.innerHTML = `
      <strong>Book Found:</strong> ${escapeHtml(found.title)} by ${escapeHtml(found.author)}<br>
      <span class="text-xs">Available: ${found.available_copies} of ${found.total_copies} copies</span>
      <div style="margin-top: 8px;">
        <button class="btn-card-issue" style="padding: 6px 12px; font-size: 0.8rem;" onclick="quickIssueBook(${found.id}); document.getElementById('barcodeModal').classList.add('hidden');">
          Issue This Book &rarr;
        </button>
      </div>
    `;
  } else {
    resultBox.classList.remove("hidden");
    resultBox.innerHTML = `<span style="color: #DC2626;">No book found matching barcode "${escapeHtml(code)}".</span>`;
  }
}

// ------------------ EVENT LISTENERS & SETUP ------------------

document.addEventListener("DOMContentLoaded", () => {
  // Check active session
  checkSession();
  setLanguage(state.language);

  // Nav Item click
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      if (view) switchView(view);
    });
  });

  // Mobile drawer toggle
  document.getElementById("mobileToggle")?.addEventListener("click", () => {
    document.getElementById("sidebar")?.classList.toggle("mobile-open");
  });

  // Language selector
  document.getElementById("languageSelect")?.addEventListener("change", (e) => {
    setLanguage(e.target.value);
  });

  // 1-Click Demo Logins
  document.getElementById("demoAdminBtn")?.addEventListener("click", () => {
    document.getElementById("loginEmail").value = "admin@lms.com";
    document.getElementById("loginPassword").value = "admin123";
    document.getElementById("loginForm")?.dispatchEvent(new Event("submit"));
  });

  document.getElementById("demoStudentBtn")?.addEventListener("click", () => {
    document.getElementById("loginEmail").value = "student@lms.com";
    document.getElementById("loginPassword").value = "student123";
    document.getElementById("loginForm")?.dispatchEvent(new Event("submit"));
  });

  // Auth Forms
  document.getElementById("loginForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    try {
      const data = await api("/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      if (data.success) {
        setAuth(data.user, data.token);
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  document.getElementById("signupForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("signupName").value;
    const email = document.getElementById("signupEmail").value;
    const password = document.getElementById("signupPassword").value;
    const role = document.getElementById("signupRole").value;
    const preferred_language = document.getElementById("signupLanguage").value;

    try {
      const data = await api("/register", {
        method: "POST",
        body: JSON.stringify({ name, email, password, role, preferred_language })
      });
      if (data.success) {
        setAuth(data.user, data.token);
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  document.getElementById("logoutBtn")?.addEventListener("click", async () => {
    try {
      await api("/logout", { method: "POST" });
    } catch (e) {}
    clearAuth();
  });

  // Hero Quick Actions
  document.getElementById("heroQuickIssueBtn")?.addEventListener("click", () => {
    switchView("circulation");
  });

  document.getElementById("scanBarcodeBtn")?.addEventListener("click", () => {
    simulateBarcodeLookup("BOOK-1001");
  });

  // Live Book Search
  const searchInput = document.getElementById("bookSearchInput");
  const suggestionsBox = document.getElementById("searchSuggestionsBox");
  const clearBtn = document.getElementById("searchClearBtn");

  let debounceTimer;
  searchInput?.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    if (clearBtn) clearBtn.classList.toggle("hidden", val.length === 0);

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      loadBooks();
      if (val.length >= 2) {
        try {
          const data = await api(`/search-suggestions?q=${encodeURIComponent(val)}`);
          if (data.success && data.suggestions.length > 0) {
            suggestionsBox.innerHTML = data.suggestions.map((s) => `
              <div class="suggestion-item" data-label="${escapeHtml(s.label)}">
                <span class="suggestion-label">${escapeHtml(s.label)}</span>
                <span class="suggestion-tag">${s.type}</span>
              </div>
            `).join("");
            suggestionsBox.classList.remove("hidden");

            suggestionsBox.querySelectorAll(".suggestion-item").forEach((item) => {
              item.addEventListener("click", () => {
                searchInput.value = item.dataset.label;
                suggestionsBox.classList.add("hidden");
                loadBooks();
              });
            });
          } else {
            suggestionsBox.classList.add("hidden");
          }
        } catch (err) {}
      } else {
        suggestionsBox.classList.add("hidden");
      }
    }, 250);
  });

  clearBtn?.addEventListener("click", () => {
    searchInput.value = "";
    clearBtn.classList.add("hidden");
    suggestionsBox.classList.add("hidden");
    loadBooks();
  });

  document.addEventListener("click", (e) => {
    if (!suggestionsBox?.contains(e.target) && e.target !== searchInput) {
      suggestionsBox?.classList.add("hidden");
    }
  });

  // Available Only Toggle
  document.getElementById("availableOnlyToggle")?.addEventListener("change", (e) => {
    state.availableOnly = e.target.checked;
    loadBooks();
  });

  // View Mode Switcher (Grid vs Table)
  document.getElementById("viewModeGrid")?.addEventListener("click", () => {
    state.viewMode = "grid";
    document.getElementById("viewModeGrid")?.classList.add("active");
    document.getElementById("viewModeTable")?.classList.remove("active");
    document.getElementById("booksGrid")?.classList.remove("hidden");
    document.getElementById("booksTableView")?.classList.add("hidden");
  });

  document.getElementById("viewModeTable")?.addEventListener("click", () => {
    state.viewMode = "table";
    document.getElementById("viewModeTable")?.classList.add("active");
    document.getElementById("viewModeGrid")?.classList.remove("hidden");
    document.getElementById("booksGrid")?.classList.add("hidden");
    document.getElementById("booksTableView")?.classList.remove("hidden");
  });

  // Issue Book Form
  document.getElementById("issueForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const book_id = document.getElementById("issueBookSelect").value;
    const days = document.getElementById("issueDays").value;
    const payload = { book_id, days };

    if (state.user?.role === "admin") {
      const userSelect = document.getElementById("issueUserSelect");
      if (userSelect && userSelect.value) {
        payload.user_id = userSelect.value;
      }
    }

    try {
      const data = await api("/issue-book", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      if (data.success) {
        showToast(data.message, "success");
        await loadAllData();
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Add Book Form (Admin)
  document.getElementById("addBookForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      title: document.getElementById("bookTitle").value,
      author: document.getElementById("bookAuthor").value,
      category: document.getElementById("bookCategory").value,
      isbn: document.getElementById("bookIsbn").value,
      barcode: document.getElementById("bookBarcode").value,
      total_copies: document.getElementById("bookTotalCopies").value,
      description: document.getElementById("bookDescription").value
    };

    try {
      const data = await api("/add-book", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      if (data.success) {
        showToast(data.message, "success");
        document.getElementById("addBookForm").reset();
        switchView("books");
        loadBooks();
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Auto Barcode Generator
  document.getElementById("genBarcodeBtn")?.addEventListener("click", () => {
    const code = `BOOK-${Date.now().toString().slice(-5)}`;
    document.getElementById("bookBarcode").value = code;
  });

  // Edit Book Form
  document.getElementById("editBookForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const bookId = document.getElementById("editBookId").value;
    const payload = {
      title: document.getElementById("editTitle").value,
      author: document.getElementById("editAuthor").value,
      category: document.getElementById("editCategory").value,
      isbn: document.getElementById("editIsbn").value,
      barcode: document.getElementById("editBarcode").value,
      total_copies: document.getElementById("editTotalCopies").value,
      description: document.getElementById("editDescription").value
    };

    try {
      const data = await api(`/books/${bookId}`, {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      if (data.success) {
        showToast(data.message, "success");
        document.getElementById("editBookModal")?.classList.add("hidden");
        loadBooks();
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Barcode Modal controls
  document.getElementById("closeBarcodeModal")?.addEventListener("click", () => {
    document.getElementById("barcodeModal")?.classList.add("hidden");
  });
  document.getElementById("closeBarcodeModalBtn")?.addEventListener("click", () => {
    document.getElementById("barcodeModal")?.classList.add("hidden");
  });
  document.getElementById("barcodeLookupBtn")?.addEventListener("click", () => {
    const val = document.getElementById("barcodeInput")?.value || "";
    renderBarcodeSvg(val);
    performBarcodeSearch(val);
  });

  document.querySelectorAll(".btn-sample-code").forEach((btn) => {
    btn.addEventListener("click", () => {
      const code = btn.dataset.code;
      document.getElementById("barcodeInput").value = code;
      renderBarcodeSvg(code);
      performBarcodeSearch(code);
    });
  });

  // Payment Modal controls
  document.getElementById("closePaymentModal")?.addEventListener("click", () => {
    document.getElementById("paymentModal")?.classList.add("hidden");
  });
  document.getElementById("closePaymentModalBtn")?.addEventListener("click", () => {
    document.getElementById("paymentModal")?.classList.add("hidden");
  });

  document.querySelectorAll(".payment-method-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".payment-method-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      const method = card.querySelector("input").value;
      const qrBox = document.getElementById("upiQrSection");
      if (qrBox) qrBox.classList.toggle("hidden", method !== "UPI");
    });
  });

  document.getElementById("confirmPaymentBtn")?.addEventListener("click", async () => {
    const txId = document.getElementById("payModalTxId")?.value;
    const activeMethod = document.querySelector(".payment-method-card.active input")?.value || "UPI";

    try {
      const data = await api("/pay-fine", {
        method: "POST",
        body: JSON.stringify({ transaction_id: txId, payment_method: activeMethod })
      });
      if (data.success) {
        showToast(data.message, "success");
        document.getElementById("paymentModal")?.classList.add("hidden");
        await loadAllData();
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Edit Modal close
  document.getElementById("closeEditModal")?.addEventListener("click", () => {
    document.getElementById("editBookModal")?.classList.add("hidden");
  });
  document.getElementById("closeEditModalBtn")?.addEventListener("click", () => {
    document.getElementById("editBookModal")?.classList.add("hidden");
  });

  // Notifications Drawer
  document.getElementById("notificationsBtn")?.addEventListener("click", () => {
    document.getElementById("notificationsDrawer")?.classList.remove("hidden");
  });
  document.getElementById("closeDrawerBtn")?.addEventListener("click", () => {
    document.getElementById("notificationsDrawer")?.classList.add("hidden");
  });

  // Circulation Filter Tabs
  document.querySelectorAll("#txFilterTabs .filter-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#txFilterTabs .filter-pill").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderTransactions(btn.dataset.filter);
    });
  });
});

// Helper for escaping HTML injection
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
