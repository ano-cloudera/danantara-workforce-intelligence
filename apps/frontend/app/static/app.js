const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const api = window.WorkforceAPI;

const state = {
  candidates: [],
  positions: [],
  summary: null,
  config: null,
  health: null,
  matches: [],
  matchPosition: null,
  uploads: [],
  sourceInventory: null,
  policySessionId: null,
  policyRequestId: null,
  policySources: [],
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function icon(name, context = "button", className = "") {
  return `<span data-icon="${escapeHtml(name)}" data-context="${context}"${className ? ` data-icon-class="${escapeHtml(className)}"` : ""}></span>`;
}

function refreshIcons() {
  window.renderLucideIcons?.();
}

function notify(message, type = "success") {
  const banner = $("#app-banner");
  banner.textContent = message;
  banner.className = `toast show ${type}`;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => banner.className = "toast", 4200);
}

function showPage(name) {
  $$(".page").forEach(page => page.classList.toggle("active", page.id === `page-${name}`));
  $$(".nav").forEach(nav => nav.classList.toggle("active", nav.dataset.page === name));
  $("#sidebar").classList.remove("open");
  window.scrollTo({ top: 0, behavior: "smooth" });
  history.replaceState(null, "", `#${name}`);
  refreshIcons();
}

function closeGlobalSearch() {
  $("#global-search-wrap").classList.remove("open");
  $("#global-search-results").classList.remove("show");
  $("#global-search").setAttribute("aria-expanded", "false");
}

function openGlobalSearch() {
  $("#global-search-wrap").classList.add("open");
  $("#global-search").focus();
}

function activateSearchResult(result) {
  closeGlobalSearch();
  showPage(result.page || "overview");
  if (result.type === "position") {
    $("#position").value = result.id;
  } else if (result.type === "skill") {
    $("#skills").value = result.title;
  } else if (result.type === "candidate") {
    $("#talent-company").value = result.subtitle.split(" · ").at(-1) || "";
    notify(`${result.title} selected. Run Match to refresh the governed ranking.`);
  } else if (result.type === "policy") {
    $("#policy-question").value = `Summarize the key workforce rules in ${result.title}.`;
  }
}

function renderSearchResults(data) {
  const container = $("#global-search-results");
  const labels = {
    candidates: "Candidates",
    positions: "Positions",
    skills: "Skills",
    policies: "Policies",
  };
  const groups = Object.entries(data.groups || {}).filter(([, items]) => items.length);
  if (!groups.length) {
    container.innerHTML = `<div class="search-empty">No result for “${escapeHtml(data.query)}”.</div>`;
  } else {
    container.innerHTML = groups.map(([name, items]) => `<section><h3>${labels[name] || escapeHtml(name)}</h3>${items.map(item => `<button type="button" class="search-result" role="option" data-result='${escapeHtml(JSON.stringify(item))}'><span>${icon(item.type === "policy" ? "files" : item.type === "position" ? "briefcase-business" : item.type === "skill" ? "target" : "users")}</span><span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.subtitle)}</small></span><span>${icon("arrow-right")}</span></button>`).join("")}</section>`).join("");
  }
  container.classList.add("show");
  $("#global-search").setAttribute("aria-expanded", "true");
  container.querySelectorAll(".search-result").forEach(button => {
    button.onclick = () => activateSearchResult(JSON.parse(button.dataset.result));
  });
  refreshIcons();
}

async function searchGlobally(term) {
  if (term.length < 2) {
    $("#global-search-results").classList.remove("show");
    return;
  }
  try {
    renderSearchResults(await api.get(`search?q=${encodeURIComponent(term)}&limit=5`));
  } catch (error) {
    $("#global-search-results").innerHTML = `<div class="search-empty">${escapeHtml(error.message)}</div>`;
    $("#global-search-results").classList.add("show");
  }
}

function metricCard(iconName, tone, label, value, note) {
  return `<article class="metric-card card"><span class="stat-icon ${tone}">${icon(iconName, "stat")}</span><div><small>${escapeHtml(label)}</small><strong class="value">${escapeHtml(value)}</strong><small>${escapeHtml(note)}</small></div></article>`;
}

function statusRow(label, value, ok = true) {
  return `<div class="status-row">${icon(ok ? "badge-check" : "circle-alert")}<span>${escapeHtml(label)}</span><strong class="${ok ? "success-text" : ""}">${escapeHtml(value)}</strong></div>`;
}

function renderOverview() {
  const entities = [...new Set(state.candidates.map(candidate => candidate.company).filter(Boolean))];
  const policyCount = state.summary?.policy_documents ?? 3;
  const average = state.matches.length
    ? (state.matches.reduce((sum, item) => sum + item.match_score, 0) / state.matches.length).toFixed(1)
    : "Not run";
  $("#overview-metrics").innerHTML = [
    metricCard("users", "red", "Total Candidates", state.candidates.length, "Current PoC records"),
    metricCard("briefcase-business", "blue", "Active Recruitment Requests", state.positions.length, "PoC positions"),
    metricCard("gauge", "green", "Average Match Score", average, state.matches.length ? "Latest browser session" : "Run Talent Match"),
    metricCard("database", "purple", "Entities", entities.length, entities.join(" · ") || "No data"),
    metricCard("files", "amber", "Policy Documents", policyCount, "Configured PoC sources"),
  ].join("");

  $("#system-health").innerHTML = [
    statusRow("Backend API", state.health?.status === "ok" ? "Healthy" : "Unavailable", state.health?.status === "ok"),
    statusRow("Gemini configuration", state.health?.gemini?.configured ? "Configured" : "Not configured", Boolean(state.health?.gemini?.configured)),
    statusRow("Qdrant", state.health?.qdrant ? "Healthy" : "Unavailable", Boolean(state.health?.qdrant)),
    statusRow("Data mode", state.config?.data_mode || "Unknown", true),
  ].join("");
  renderRecentMatches();
  refreshIcons();
}

function renderRecentMatches() {
  const containers = [$("#recent-matches"), $("#dashboard-recent")];
  const position = state.matchPosition;
  containers.forEach(container => {
    if (!container) return;
    if (!state.matches.length) {
      container.innerHTML = `<div class="empty-state compact">${icon("scan-search", "stat")}<h3>No matching activity yet</h3><p>Run Talent Match to populate ranked candidate results.</p></div>`;
      return;
    }
    const rows = state.matches.slice(0, 4).map((item, index) => {
      const candidate = item.candidate;
      const initials = candidate.name.split(/\s+/).map(part => part[0]).slice(0, 2).join("");
      const score = Number(item.match_score) || 0;
      const scoreTone = score >= 80 ? "strong" : score >= 60 ? "review" : "low";
      const scoreLabel = score >= 80 ? "Strong match" : score >= 60 ? "Review match" : "Skill gaps";
      return `<button type="button" class="match-activity-row candidate-details" data-candidate="${escapeHtml(candidate.candidate_id)}" aria-label="Open ${escapeHtml(candidate.name)} details">
        <span class="activity-rank">${index + 1}</span>
        <span class="activity-candidate"><span class="activity-avatar">${escapeHtml(initials)}</span><span><strong>${escapeHtml(candidate.name)}</strong><small>${escapeHtml(candidate.company || "Entity unavailable")} · ${escapeHtml(candidate.years_experience)} years</small></span></span>
        <span class="activity-context"><strong>${escapeHtml(position?.title || "Latest talent match")}</strong><small>${escapeHtml(item.matched_skills?.length || 0)} skills matched · ${escapeHtml(item.skill_gaps?.length || 0)} gaps</small></span>
        <span class="activity-score ${scoreTone}"><strong>${escapeHtml(score)}%</strong><small>${scoreLabel}</small></span>
        <span class="activity-open">${icon("arrow-right")}</span>
      </button>`;
    }).join("");
    container.innerHTML = `<div class="match-activity-table"><div class="match-activity-head"><span>Rank</span><span>Candidate</span><span>Matching context</span><span>Score</span><span></span></div>${rows}</div>`;
  });
  $$(".match-activity-row.candidate-details").forEach(button => {
    button.onclick = () => openCandidateDetail(button.dataset.candidate);
  });
  refreshIcons();
}

function populateFilters() {
  const positionTitles = [...new Set(state.positions.map(position => position.title))];
  const positionOptions = positionTitles.map(title => `<option value="${escapeHtml(title)}">${escapeHtml(title)}</option>`).join("");
  $("#position").innerHTML = positionOptions || "<option value=''>No positions available</option>";
  $("#candidate-position").innerHTML = state.positions.map(position => `<option value="${escapeHtml(position.title)}">${escapeHtml(position.title)}</option>`).join("") || "<option value=''>No positions available</option>";
  const talentEntities = [...new Set(state.candidates.map(candidate => candidate.company).filter(Boolean))].sort();
  const policyEntities = [...new Set([
    ...talentEntities,
    ...(state.sourceInventory?.documents || []).map(document => document.entity).filter(Boolean),
  ])].sort();
  $("#talent-company").innerHTML = `<option value="">All PoC entities</option>${talentEntities.map(entity => `<option>${escapeHtml(entity)}</option>`).join("")}`;
  $("#entity-options").innerHTML = policyEntities.map(entity => `<label class="check-chip"><input type="checkbox" value="${escapeHtml(entity)}" ${talentEntities.includes(entity) ? "checked" : ""} /><span>${escapeHtml(entity)}</span></label>`).join("");
}

function chips(items, gap = false) {
  if (!items?.length) return `<span class="muted">None</span>`;
  return `<div class="chips">${items.map(item => `<span class="chip${gap ? " gap" : ""}">${escapeHtml(item)}</span>`).join("")}</div>`;
}

async function openCandidateDetail(candidateId) {
  const dialog = $("#candidate-dialog");
  $("#candidate-detail").innerHTML = `<div class="skeleton wide"></div>`;
  dialog.showModal();
  try {
    const candidate = await api.get(`candidates/${encodeURIComponent(candidateId)}`);
    const proficiency = Object.entries(candidate.skill_proficiency || {}).sort((a, b) => b[1] - a[1]);
    const initials = candidate.name.split(/\s+/).map(part => part[0]).slice(0, 2).join("");
    $("#candidate-detail").innerHTML = `<header class="candidate-detail-header"><span class="candidate-avatar">${escapeHtml(initials)}</span><div><span class="eyebrow">SAFE POC PROFILE</span><h2>${escapeHtml(candidate.name)}</h2><p>${escapeHtml(candidate.current_title || "Current title unavailable")} · ${escapeHtml(candidate.company || "Entity unavailable")}</p></div></header>
      <div class="candidate-detail-grid">
        <section><h3>Application</h3>${statusRow("Stage", candidate.application_stage || "Unavailable", true)}${statusRow("Status", candidate.application_status || "Unavailable", true)}${statusRow("Salary-band compliance", candidate.salary_compliance || "Unavailable", candidate.salary_compliance === "WITHIN_BAND")}</section>
        <section><h3>Profile</h3>${statusRow("Experience", `${candidate.years_experience} years`, true)}${statusRow("Education", candidate.education_level || "Unavailable", true)}${statusRow("Institution", candidate.education_institution || "Unavailable", true)}</section>
      </div>
      <section class="candidate-detail-section"><h3>Skills and sample proficiency</h3><div class="proficiency-list">${proficiency.map(([skill, score]) => score ? `<div><span>${escapeHtml(skill)}</span><progress max="5" value="${escapeHtml(score)}"></progress><strong>${escapeHtml(score)}/5</strong></div>` : `<div><span>${escapeHtml(skill)}</span><small class="muted">Proficiency not assessed</small></div>`).join("") || (candidate.skills || []).map(skill => `<div><span>${escapeHtml(skill)}</span><small class="muted">Proficiency not assessed</small></div>`).join("") || "<p class='muted'>No skill data.</p>"}</div></section>
      <section class="candidate-detail-section"><h3>Experience</h3>${(candidate.experiences || []).map(item => `<article class="experience-item"><strong>${escapeHtml(item.role_title)}</strong><span>${escapeHtml(item.employer)} · ${escapeHtml(item.start_date)}–${escapeHtml(item.is_current ? "Present" : (item.end_date || "Present"))}</span><p>${escapeHtml(item.description)}</p></article>`).join("") || "<p class='muted'>No experience history.</p>"}</section>
      <section class="candidate-detail-section"><h3>Source coverage</h3>${chips(candidate.source_documents || [])}<p class="privacy-note">Direct identifiers and protected HR attributes are intentionally excluded from this browser response.</p></section>`;
    refreshIcons();
  } catch (error) {
    $("#candidate-detail").innerHTML = `<div class="empty-state">${icon("circle-alert", "stat")}<h3>Candidate detail unavailable</h3><p>${escapeHtml(error.message)}</p></div>`;
    refreshIcons();
  }
}

function renderTalent(matches) {
  const container = $("#talent-results");
  if (!matches.length) {
    container.innerHTML = `<div class="empty-state card">${icon("scan-search", "stat")}<h3>No matching candidates</h3><p>Try all entities or remove optional skill keywords.</p></div>`;
    refreshIcons();
    return;
  }
  container.innerHTML = matches.map((match, index) => {
    const candidate = match.candidate;
    const initials = candidate.name.split(/\s+/).map(part => part[0]).slice(0, 2).join("");
    return `<article class="candidate-card card">
      <div class="rank-score"><span class="rank-ribbon">${index + 1}</span><span class="score-ring">${escapeHtml(match.match_score)}</span><small>Match Score</small></div>
      <div class="candidate-identity"><span class="candidate-avatar">${escapeHtml(initials)}</span><div><h3>${escapeHtml(candidate.name)}</h3><p>${escapeHtml(candidate.summary || "Profile summary not available")}</p><span class="candidate-meta">${icon("briefcase")} ${escapeHtml(candidate.company || "Company not available")} · ${escapeHtml(candidate.years_experience)} years</span></div></div>
      <div class="skill-column"><strong>Matched Skills</strong>${chips(match.matched_skills)}<strong>Skill Gaps</strong>${chips(match.skill_gaps, true)}</div>
      <div class="reasoning"><strong>AI Reasoning Summary</strong><p>${escapeHtml(match.reasoning || "Reasoning not available")}</p><span class="badge warning">Human review required</span> <button class="text-button candidate-details" data-candidate="${escapeHtml(candidate.candidate_id)}">View Details ${icon("arrow-right")}</button></div>
    </article>`;
  }).join("");
  $$(".candidate-details").forEach(button => button.onclick = () => {
    openCandidateDetail(button.dataset.candidate);
  });
  refreshIcons();
}

async function runTalentMatch() {
  const container = $("#talent-results");
  const selectedTitle = $("#position").value;
  const selectedCompany = $("#talent-company").value;
  const button = $("#run-match");
  button.disabled = true;
  button.innerHTML = `${icon("send")} Matching...`;
  container.innerHTML = `<div class="card empty-state"><div class="skeleton wide"></div><p>Running governed candidate scoring...</p></div>`;
  try {
    const data = await api.post("talent/match", {
      position_title: selectedTitle || null,
      company: selectedCompany || null,
      skills_keywords: $("#skills").value.split(",").map(item => item.trim()).filter(Boolean),
      top_n: 5,
    });
    state.matches = data.matches || [];
    state.matchPosition = data.position || null;
    renderTalent(state.matches);
    renderOverview();
    renderDashboard();
    notify(`Matching completed for ${state.matches.length} candidate(s).`);
  } catch (error) {
    container.innerHTML = `<div class="card empty-state">${icon("circle-alert", "stat")}<h3>Talent Match unavailable</h3><p>${escapeHtml(error.message)}</p></div>`;
    notify(error.message, "error");
  } finally {
    button.disabled = false;
    button.innerHTML = `${icon("send")} Run Match`;
    refreshIcons();
  }
}

function selectedEntities() {
  return $$("#entity-options input:checked").map(input => input.value);
}

function policyApiPath(path) {
  return String(path || "").replace(/^\/api\/v1\//, "/api-proxy/");
}

function renderPolicySources(sources) {
  state.policySources = sources || [];
  $("#policy-source-count").textContent = state.policySources.length;
  $("#policy-source-list").className = state.policySources.length ? "policy-source-list" : "empty-state compact";
  $("#policy-source-list").innerHTML = state.policySources.length
    ? state.policySources.map((source, index) => `<article class="policy-source-card" id="citation-${index + 1}">
        <div><em>${index + 1}</em><span><strong>${escapeHtml(source.title)}</strong><small>${escapeHtml(source.entity || "Entity unavailable")} · ${escapeHtml(source.document_type || "Policy source")} · ${source.page ? `page ${escapeHtml(source.page)}` : "section unavailable"}</small></span></div>
        ${source.section ? `<p class="source-section">${escapeHtml(source.section)}</p>` : ""}
        <p>${escapeHtml(source.text_excerpt || "No excerpt returned.")}</p>
        <div class="source-actions">${source.download_url ? `<a class="text-button" href="${escapeHtml(policyApiPath(source.download_url))}" target="_blank" rel="noopener">Download source ${icon("download")}</a>` : ""}</div>
      </article>`).join("")
    : "No grounded sources were returned. Check Qdrant indexing or the supplied fallback documents.";
  refreshIcons();
}

function appendPolicyMessage(role, content, data = null) {
  const conversation = $("#policy-conversation");
  conversation.querySelector(".policy-welcome")?.remove();
  const row = document.createElement("div");
  row.className = `chat-row ${role}-row`;
  const article = document.createElement("article");
  article.className = `chat-message ${role}`;
  if (role === "user") {
    row.innerHTML = `<span class="chat-avatar user">AP</span>`;
    article.innerHTML = `<div class="message-label">You</div><div class="message-body">${escapeHtml(content)}</div>`;
  } else if (role === "loading") {
    row.innerHTML = `<span class="chat-avatar assistant">${icon("book-open-check")}</span>`;
    article.innerHTML = `<div class="message-label">Policy Intelligence</div><div class="message-body"><div class="typing"><i></i><i></i><i></i></div></div>`;
  } else {
    const sources = data?.sources || [];
    const chart = data?.chart;
    const responseKind = data?.response_kind || "grounded";
    const badge = responseKind === "conversational"
      ? `<span class="badge">Assistant</span>`
      : responseKind === "data"
        ? `<span class="badge success">Live data</span>`
        : `<span class="badge success">Grounded response</span>`;
    const citationLinks = sources.map((source, index) => `<a href="#citation-${index + 1}" class="citation-chip">[${index + 1}] ${escapeHtml(source.entity || "Source")}</a>`).join("");
    const chartBlock = chart?.items?.length ? `<div class="message-chart"><h4>${escapeHtml(chart.title)}</h4><div class="bar-chart">${bars(chart.items)}</div></div>` : "";
    const citationsBlock = responseKind === "grounded" ? `<div class="message-citations">${citationLinks || "<span class='muted'>No citations returned</span>"}</div>` : "";
    const suggestions = (data?.suggested_questions || []).map(question => `<button type="button" class="follow-up" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>`).join("");
    const actions = data?.request_id ? `<div class="message-actions">
        <button type="button" data-action="copy" aria-label="Copy answer">${icon("copy")} Copy</button>
        <button type="button" data-action="up" aria-label="Helpful answer">${icon("thumbs-up")}</button>
        <button type="button" data-action="down" aria-label="Unhelpful answer">${icon("thumbs-down")}</button>
        <button type="button" data-action="export" aria-label="Export answer to PDF">${icon("download")} Export PDF</button>
      </div>` : "";
    article.dataset.requestId = data?.request_id || "";
    row.innerHTML = `<span class="chat-avatar assistant">${icon("book-open-check")}</span>`;
    article.innerHTML = `<div class="message-label">Policy Intelligence ${badge}</div>
      <div class="message-body answer-text">${escapeHtml(content)}</div>
      ${chartBlock}
      ${citationsBlock}
      ${actions}
      ${suggestions ? `<div class="follow-ups"><small>Suggested follow-ups</small>${suggestions}</div>` : ""}`;
  }
  row.appendChild(article);
  conversation.appendChild(row);
  conversation.scrollTop = conversation.scrollHeight;
  refreshIcons();
  return row;
}

async function submitPolicyFeedback(requestId, rating, button) {
  try {
    await api.post("feedback", {
      session_id: state.policySessionId,
      request_id: requestId,
      rating,
    });
    button.classList.add("selected");
    notify("Thanks, your feedback was recorded.");
  } catch (error) {
    notify(error.message, "error");
  }
}

async function runPolicy(event, suggestedQuestion = null) {
  event?.preventDefault?.();
  const button = $("#run-policy");
  const question = (suggestedQuestion || $("#policy-question").value).trim();
  const entities = selectedEntities();
  if (!question) return;
  if (!entities.length) return notify("Select at least one entity.", "error");
  appendPolicyMessage("user", question);
  $("#policy-question").value = "";
  const loading = appendPolicyMessage("loading", "");
  button.disabled = true;
  button.innerHTML = `${icon("book-open-check")} Reviewing sources...`;
  try {
    const documentType = $("#policy-document-type").value;
    const data = await api.post("policy/chat", {
      message: question,
      session_id: state.policySessionId,
      filters: {
        entities,
        topics: [$("#policy-topic").value],
        document_types: documentType ? [documentType] : [],
      },
      retrieval: { top_k: 6 },
    });
    loading.remove();
    state.policySessionId = data.session_id;
    state.policyRequestId = data.request_id;
    appendPolicyMessage("assistant", data.answer || "No answer returned.", data);
    renderPolicySources(data.sources || []);
    notify(`Grounded answer completed with ${(data.sources || []).length} source(s).`);
  } catch (error) {
    loading.remove();
    appendPolicyMessage("assistant", `Policy analysis is unavailable: ${error.message}`, { sources: [] });
    notify(error.message, "error");
  } finally {
    button.disabled = false;
    button.innerHTML = `${icon("send")} Send`;
    refreshIcons();
  }
}

function resetPolicyChat() {
  state.policySessionId = null;
  state.policyRequestId = null;
  state.policySources = [];
  $("#policy-conversation").innerHTML = `<div class="policy-welcome"><span class="stat-icon purple">${icon("book-open-check", "stat")}</span><h2>Hi, I'm Policy Intelligence</h2><p>I answer workforce policy questions using the Group policy, PKB, and salary documents supplied for this PoC, and I cite the source for every answer.</p><p class="policy-welcome-hint">Pick a source filter above, then ask a question.</p></div>`;
  renderPolicySources([]);
  refreshIcons();
}

function bars(items, colorClass = "") {
  if (!items?.length) return `<div class="empty-state compact">No data available.</div>`;
  const max = Math.max(...items.map(item => Number(item[1]) || 0), 1);
  return items.map(item => `<div class="bar-row"><span>${escapeHtml(item[0])}</span><div class="bar-track"><div class="bar-fill ${colorClass}" style="width:${Math.max(4, (Number(item[1]) / max) * 100)}%"></div></div><strong>${escapeHtml(item[1])}</strong></div>`).join("");
}

function renderDashboard() {
  const summary = state.summary || {};
  const topSkill = summary.top_skills?.[0]?.[0] || "Not available";
  const average = state.matches.length
    ? (state.matches.reduce((sum, item) => sum + item.match_score, 0) / state.matches.length).toFixed(1)
    : summary.average_match_score ?? "Not available";
  $("#dashboard-metrics").innerHTML = [
    metricCard("users", "red", "Total Candidates", summary.total_candidates ?? state.candidates.length, "PoC sample"),
    metricCard("briefcase-business", "blue", "Active Recruitment Requests", summary.active_recruitment_requests ?? state.positions.length, `${summary.active_openings ?? "—"} current opening(s)`),
    metricCard("gauge", "green", "Average Match Score", average, "Latest browser session"),
    metricCard("layers-3", "purple", "Top Skill Category", topSkill, "Current profiles"),
    metricCard("files", "amber", "Policy Documents", summary.policy_documents ?? 3, "Configured sources"),
  ].join("");
  $("#company-bars").innerHTML = bars(summary.by_company || []);
  $("#skill-bars").innerHTML = bars(summary.top_skills || []);
  if ($("#recruitment-bars")) $("#recruitment-bars").innerHTML = bars(summary.recruitment_stages || []);
  $("#snapshot-panel").innerHTML = `<span class="muted">Current candidate records</span><strong class="snapshot-number">${escapeHtml(summary.total_candidates ?? state.candidates.length)}</strong>${statusRow("Entities represented", String(new Set(state.candidates.map(item => item.company)).size), true)}${statusRow("Qdrant health", state.health?.qdrant ? "Healthy" : "Unavailable", Boolean(state.health?.qdrant))}${statusRow("Historical trend", "Not available", false)}`;
  renderRecentMatches();
  refreshIcons();
}

function renderSources() {
  const entities = [...new Set(state.candidates.map(candidate => candidate.company).filter(Boolean))];
  const steps = [
    ["Upload / Source Input", "PDF and candidate form intake", "Input"],
    ["Cloudera DataFlow (NiFi)", "Validation and governed routing", "Primary"],
    ["OCR / Extraction", "Document parsing and metadata", "Process"],
    ["Iceberg Raw", "Original governed source state", "Lakehouse"],
    ["Curated Iceberg", "Standardized workforce data", "Curated"],
    ["Impala / CDW", "Analytics-ready structured serving", "Serving"],
    ["Embedding → Qdrant", "Secondary AI indexing path", "AI index"],
  ];
  $("#pipeline").innerHTML = steps.map((step, index) => `<li><span class="pipeline-index">${index + 1}</span><div><strong>${escapeHtml(step[0])}</strong><p>${escapeHtml(step[1])}</p></div><span class="badge ${index === 6 ? "warning" : "success"}">${escapeHtml(step[2])}</span></li>`).join("");
  const documentCount = state.sourceInventory?.documents?.length ?? 0;
  $("#source-summary").innerHTML = `<div class="mini-metric"><small>Candidates</small><strong>${state.candidates.length}</strong><small>PoC records</small></div><div class="mini-metric"><small>Positions</small><strong>${state.positions.length}</strong><small>Job openings</small></div><div class="mini-metric"><small>Documents</small><strong>${documentCount}</strong><small>Supplied raw sources</small></div>`;
  $("#connected-sources").innerHTML = entities.map(entity => statusRow(`${entity} PoC source`, "Connected", true)).join("");
  const uploads = state.sourceInventory?.uploads || [];
  if (uploads.length) {
    $("#recent-uploads").innerHTML = uploads.map(item => `<div class="table-row"><strong>${escapeHtml(item.file_name)}</strong><span>${escapeHtml(item.metadata?.entity || "Unassigned")}</span><b class="success-text">${escapeHtml(item.status)}</b></div>`).join("");
  }
  refreshIcons();
}

function renderSettings() {
  const config = state.config;
  if (!config) {
    $("#runtime-config").innerHTML = `<div class="empty-state compact">Runtime configuration unavailable.</div>`;
    return;
  }
  const values = [
    ["Environment", config.environment],
    ["Data mode", config.data_mode],
    ["Orchestration", config.orchestrator_mode],
    ["Gemini text model", config.gemini_text_model],
    ["Gemini embedding model", config.gemini_embedding_model],
    ["Guardrails", config.guardrails_mode],
    ["Qdrant", config.services?.qdrant_healthy ? "Healthy" : "Unavailable"],
  ];
  $("#runtime-config").innerHTML = values.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value || "Not available")}</strong></div>`).join("");
}

function showInline(selector, message, type) {
  const element = $(selector);
  element.className = `inline-status show ${type}`;
  element.textContent = message;
}

async function submitUpload(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    const result = await api.upload(new FormData(form));
    const filename = form.elements.file.files[0]?.name || "Uploaded document";
    state.uploads.unshift({ filename, entity: form.elements.entity.value, status: result.status || "accepted" });
    $("#recent-uploads").innerHTML = state.uploads.map(item => `<div class="table-row"><strong>${escapeHtml(item.filename)}</strong><span>${escapeHtml(item.entity)}</span><b class="success-text">${escapeHtml(item.status)}</b></div>`).join("");
    showInline("#upload-result", `Upload accepted. Routing: ${result.routing || "backend"}.`, "success");
    form.reset();
  } catch (error) {
    showInline("#upload-result", error.message, "error");
  } finally {
    button.disabled = false;
  }
}

async function submitCandidate(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  const raw = Object.fromEntries(new FormData(form).entries());
  raw.core_skills = (raw.core_skills || "").split(",").map(item => item.trim()).filter(Boolean);
  raw.years_experience = Number(raw.years_experience || 0);
  button.disabled = true;
  try {
    const result = await api.post("sources/candidate", raw);
    showInline("#candidate-result", `Candidate accepted. Submission ${result.submission_id}; routing: ${result.routing}.`, "success");
    form.reset();
  } catch (error) {
    showInline("#candidate-result", error.message, "error");
  } finally {
    button.disabled = false;
  }
}

function bindEvents() {
  $$('[data-page]').forEach(button => button.addEventListener("click", () => showPage(button.dataset.page)));
  $("#mobile-menu").onclick = () => $("#sidebar").classList.toggle("open");
  $("#candidate-dialog-close").onclick = () => $("#candidate-dialog").close();
  $("#run-match").onclick = runTalentMatch;
  ["#skills", "#position", "#talent-company"].forEach(selector => {
    $(selector).addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        runTalentMatch();
      }
    });
  });
  $("#policy-form").onsubmit = runPolicy;
  $("#policy-question").addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      $("#policy-form").requestSubmit();
    }
  });
  $("#new-policy-chat").onclick = resetPolicyChat;
  $("#policy-conversation").onclick = event => {
    const followUp = event.target.closest(".follow-up, .suggested-prompts button");
    if (followUp) return runPolicy(event, followUp.dataset.question || followUp.textContent);
    const action = event.target.closest("[data-action]");
    if (!action) return;
    const message = action.closest(".chat-message");
    const requestId = message?.dataset.requestId;
    if (action.dataset.action === "copy") {
      navigator.clipboard?.writeText(message.querySelector(".answer-text")?.textContent || "");
      notify("Answer copied.");
    } else if (action.dataset.action === "up" || action.dataset.action === "down") {
      submitPolicyFeedback(requestId, action.dataset.action === "up" ? 1 : -1, action);
    } else if (action.dataset.action === "export") {
      api.download("policy/export", { request_id: requestId }, "policy-conversation.pdf")
        .then(() => notify("Policy PDF exported."))
        .catch(error => notify(error.message, "error"));
    }
  };
  $("#upload-form").onsubmit = submitUpload;
  $("#candidate-form").onsubmit = submitCandidate;
  $("#upload-focus").onclick = () => $("#upload-form").scrollIntoView({ behavior: "smooth", block: "center" });
  $("#candidate-focus").onclick = () => $("#candidate-registration").scrollIntoView({ behavior: "smooth", block: "center" });
  $("#reset-display").onclick = () => {
    $$(".preference-row input").forEach(input => input.checked = true);
    notify("Display preferences reset for this browser session.");
  };
  $$(".settings-tabs button").forEach(button => button.onclick = () => {
    $$(".settings-tabs button").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    notify("This is a PoC display filter; settings are not persisted.");
  });
  $("#mobile-search").onclick = openGlobalSearch;
  $("#search-close").onclick = closeGlobalSearch;
  $("#global-search").addEventListener("input", event => {
    clearTimeout(searchGlobally.timer);
    const term = event.currentTarget.value.trim();
    searchGlobally.timer = setTimeout(() => searchGlobally(term), 240);
  });
  $("#global-search").addEventListener("keydown", event => {
    if (event.key === "Escape") closeGlobalSearch();
    if (event.key === "ArrowDown") {
      event.preventDefault();
      $("#global-search-results .search-result")?.focus();
    }
  });
  document.addEventListener("click", event => {
    if (!event.target.closest("#global-search-wrap") && !event.target.closest("#mobile-search")) closeGlobalSearch();
  });
  document.addEventListener("keydown", event => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openGlobalSearch();
    }
  });
}

async function loadInitialData() {
  const tasks = await Promise.allSettled([
    api.get("candidates"),
    api.get("positions"),
    api.get("dashboard/summary"),
    api.get("config/public"),
    api.get("health"),
    api.get("sources"),
  ]);
  if (tasks[0].status === "fulfilled") state.candidates = tasks[0].value;
  if (tasks[1].status === "fulfilled") state.positions = tasks[1].value;
  if (tasks[2].status === "fulfilled") state.summary = tasks[2].value;
  if (tasks[3].status === "fulfilled") state.config = tasks[3].value;
  if (tasks[4].status === "fulfilled") state.health = tasks[4].value;
  if (tasks[5].status === "fulfilled") state.sourceInventory = tasks[5].value;
  const failures = tasks.filter(task => task.status === "rejected");
  if (failures.length) notify(`${failures.length} backend resource(s) unavailable. Available PoC data is still shown.`, "error");
  populateFilters();
  renderOverview();
  renderDashboard();
  renderSources();
  renderSettings();
}

bindEvents();
showPage(location.hash.slice(1) || "overview");
loadInitialData();
