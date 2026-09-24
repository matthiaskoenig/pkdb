const $ = (id) => document.getElementById(id);
let state = { studies: [], jobs: [], github: { users: [], issues: [] } };
let csrf = '', current = '', tab = 'overview', view = 'all', signature = '', busy = false;
let selected = new Set(), pendingUpload = null, pendingRetry = null;
const el = (tag, text, className) => { const n = document.createElement(tag); if (text != null) n.textContent = String(text); if (className) n.className = className; return n; };
const button = (text, action, className) => { const n = el('button', text, className); n.type = 'button'; n.addEventListener('click', () => run(action)); return n; };
const human = (value) => String(value ?? '').replaceAll('_', ' ');
function notify(message, error = false) { $('notice').textContent = message; $('notice').className = error ? 'error' : ''; $('notice').hidden = false; }
async function api(path, body) {
  const response = await fetch(path, { credentials: 'same-origin', method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? {} : { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.detail || `Request failed (${response.status})`);
  if (data.csrf_token) csrf = data.csrf_token;
  return data;
}
async function run(action) { try { await action(); } catch (error) { notify(error.message, true); } }
async function mutate(path, body, message) { await api(path, body); if (message) notify(message); await refresh(true); }
const issueVisible = (i) => $('issue-state').value === 'all' || (i.state || 'open') === $('issue-state').value;
const issuesFor = (id) => (state.github?.issues || []).filter(i => issueVisible(i) && (i.study_ids || []).includes(id));
function assignedTo(issue, user) { return (issue.assignees || []).some(a => (typeof a === 'string' ? a : a.login) === user); }
function visibleStudies() {
  const search = $('study-search').value.toLowerCase(), scope = $('scope').value;
  return state.studies.filter(s => {
    if (search && ![s.name, s.sid, s.path].join(' ').toLowerCase().includes(search)) return false;
    if (scope && !(s.path || '').startsWith(scope + '/')) return false;
    if (view === 'assigned' && !issuesFor(s.id).some(i => assignedTo(i, state.github?.user))) return false;
    if (view === 'contributed') { const by = $('view-description').dataset.contributor || ''; return !by || JSON.stringify(s.attribution || {}).toLowerCase().includes(by.toLowerCase()); }
    return true;
  });
}
function badge(text, status = '') { return el('span', text, `badge ${['valid','created','replaced','saved','completed'].includes(status) ? 'ok' : ['invalid','failed','unknown','changed'].includes(status) ? 'warn' : ['queued','validating','uploading','waiting'].includes(status) ? 'busy' : ''}`); }
function option(select, value, text) { const item = el('option', text); item.value = value; select.append(item); }
function renderUsers() {
  const search = $('user-search').value.toLowerCase(), user = state.github?.user || '', select = $('github-user');
  select.replaceChildren(); option(select, '', 'Choose a user');
  const users = state.github?.users || [];
  for (const u of users.filter(u => `${u.login} ${u.name || ''}`.toLowerCase().includes(search) || u.login === user)) option(select, u.login, `${u.name ? u.name + ' · ' : ''}@${u.login}`);
  if (user && !users.some(u => u.login === user)) option(select, user, `@${user} (unresolved)`);
  select.value = user;
  $('github-status').textContent = [state.github?.limited ? 'Users from visible issue assignments.' : 'GitHub assignments; separate from PK-DB permissions.', state.github?.refreshed_at ? `Refreshed ${new Date(state.github.refreshed_at).toLocaleString()}.` : 'Not refreshed.', state.github?.error || ''].join(' ');
}
function render() {
  const workspace = typeof state.workspace === 'string' ? state.workspace : state.workspace?.path || '';
  $('workspace-name').textContent = workspace || 'No workspace selected';
  $('endpoint').textContent = state.endpoint || 'Not configured'; $('account').textContent = state.account || (state.authenticated ? 'API key configured; identity unverified' : 'Not authenticated');
  $('connection').textContent = state.offline ? 'Offline' : 'Local service connected';
  $('vocabulary').textContent = human(state.vocabulary?.status || 'Not checked') + (state.offline ? ' · server unchecked' : '');
  $('pause').textContent = state.paused ? 'Resume automatic actions' : 'Pause automatic actions';
  $('watch-status').textContent = state.paused ? 'Automatic actions paused' : workspace ? 'Observing source files' : 'Choose a workspace to begin';
  renderUsers();
  const scopeValue = $('scope').value; $('scope').replaceChildren(); option($('scope'), '', 'All folders');
  for (const folder of [...new Set(state.studies.map(s => (s.path || '').split('/').slice(0, -1).join('/')).filter(Boolean))].sort()) option($('scope'), folder, folder);
  $('scope').value = [...$('scope').options].some(o => o.value === scopeValue) ? scopeValue : '';
  renderStudies(); renderJobs(); if (current && !$('study-detail').contains(document.activeElement)) renderDetail();
}
function renderStudies() {
  const visible = visibleStudies(), ids = new Set(visible.map(s => s.id));
  selected = new Set([...selected].filter(id => ids.has(id)));
  $('view-title').textContent = { all: 'All local studies', assigned: 'Assigned studies', contributed: 'Contributed studies' }[view];
  $('view-description').textContent = view === 'assigned' ? `Work assigned to ${state.github?.user ? '@' + state.github.user : 'the selected GitHub user'}.` : view === 'contributed' ? `Local attribution: ${$('view-description').dataset.contributor || 'all contributors'}. This does not grant upload permissions.` : 'Open source files, review problems, and follow saved changes.';
  $('study-count').textContent = `${visible.length} of ${state.studies.length} studies`;
  document.querySelectorAll('[data-view]').forEach(n => { n.classList.toggle('active', n.dataset.view === view); n.setAttribute('aria-current', n.dataset.view === view ? 'page' : 'false'); });
  const tbody = $('studies'); tbody.replaceChildren();
  for (const s of visible) {
    const row = el('tr'); if (s.id === current) row.className = 'current';
    const checkCell = el('td'), check = el('input'); check.type = 'checkbox'; check.checked = selected.has(s.id); check.setAttribute('aria-label', `Select ${s.name || s.sid || s.id}`); check.addEventListener('change', () => { check.checked ? selected.add(s.id) : selected.delete(s.id); renderSelection(); }); checkCell.append(check); row.append(checkCell);
    const identity = el('td'); identity.append(button(s.name || s.sid || s.id, () => { current = s.id; tab = 'overview'; renderDetail(); renderStudies(); }, 'study-link'), el('div', [s.sid, s.path].filter(Boolean).join(' · '), 'small muted'));
    for (const issue of issuesFor(s.id)) { const link = safeLink(issue.html_url, `#${issue.number}`); if (link) { link.className = 'small'; identity.append(link, document.createTextNode(' ')); } } row.append(identity);
    const status = el('td'); status.append(badge(s.stale ? 'Changed since validation' : (s.status === 'valid' && state.offline ? 'Locally valid' : human(s.status || 'discovered')), s.stale ? 'changed' : s.status)); if (s.progress?.stage) status.append(el('div', human(s.progress.stage), 'small muted')); row.append(status);
    row.append(el('td', human(s.mode || 'validate'))); const upload = el('td'); upload.append(badge(human(s.last_upload?.persistence || 'Not uploaded'), s.last_upload?.persistence)); row.append(upload); tbody.append(row);
  }
  $('empty').hidden = visible.length > 0; renderSelection(); renderAssignments();
}
function renderSelection() { $('selection-count').textContent = `${selected.size} ${selected.size === 1 ? 'study' : 'studies'} selected`; document.querySelectorAll('[data-selection]').forEach(n => n.disabled = selected.size === 0); $('upload').disabled = selected.size === 0 || state.offline; const count = visibleStudies().length; $('select-all').checked = count > 0 && selected.size === count; $('select-all').indeterminate = selected.size > 0 && selected.size < count; }
function safeLink(url, text) { try { const parsed = new URL(url); if (!['http:', 'https:'].includes(parsed.protocol)) return null; const a = el('a', text); a.href = parsed.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; } catch { return null; } }
function renderAssignments() {
  const unmatched = (state.github?.issues || []).filter(i => issueVisible(i) && assignedTo(i, state.github?.user) && !(i.study_ids || []).length); $('assignments').hidden = view !== 'assigned' || !unmatched.length; $('unmatched').replaceChildren();
  for (const issue of unmatched) { const card = el('article', null, 'card assignment'); card.append(el('h3', issue.title), el('p', 'Not available locally or not matched to a unique folder.', 'small muted')); const link = safeLink(issue.html_url, `Open GitHub issue #${issue.number}`); if (link) card.append(link); const chooser = el('select'); chooser.setAttribute('aria-label', `Local folder for issue ${issue.number}`); option(chooser, '', 'Choose a local folder…'); for (const s of state.studies) option(chooser, s.id, s.path || s.name || s.id); card.append(el('br'), chooser, button('Map folder', async () => { if (!chooser.value) throw new Error('Choose a local study folder first.'); await mutate('/local/assignments/map', {number: issue.number, study_id: chooser.value}, 'Assignment mapped to the selected local folder.'); })); $('unmatched').append(card); }
}
function locationText(problem) { const l = problem.location || problem.source || {}; return [l.file || l.file_name || problem.file, l.sheet || l.sheet_name, l.cell || (l.row ? `row ${l.row}` : ''), l.path || problem.path].filter(Boolean).map(x => Array.isArray(x) ? x.join('.') : x).join(' · ') || 'No source location provided'; }
async function openFile(study, file, reveal = false) { await mutate('/local/files/open', {study_id: study.id, ...(file ? {file: typeof file === 'string' ? file : file.id || file.path} : {}), reveal}, 'Opened with the default application.'); }
function renderDetail() {
  const s = state.studies.find(s => s.id === current), container = $('study-detail'); container.hidden = !s; if (!s) return;
  container.replaceChildren(); const heading = el('div', null, 'detail-head'), name = el('div'); name.append(el('h2', s.name || s.sid || s.id), el('p', [s.sid, s.path].filter(Boolean).join(' · '), 'small muted')); heading.append(name, button('Close details', () => { current = ''; container.hidden = true; renderStudies(); })); container.append(heading);
  const controls = el('div', null, 'detail-controls'); controls.append(button('Validate', () => jobs([s.id], 'validate')), button('Upload', () => reviewUpload([s.id]), 'primary'), button('Open folder', () => openFile(s, null, true))); if (state.offline) controls.children[1].disabled = true; const serverValidate = button('Validate on server', () => jobs([s.id], 'validate_remote')); serverValidate.disabled = state.offline || !state.endpoint; controls.append(serverValidate);
  const mode = el('select'); mode.id = 'study-mode'; mode.setAttribute('aria-label', 'Action on save for this study'); for (const value of ['validate','upload','off']) option(mode, value, human(value)); mode.value = s.mode || 'validate'; mode.addEventListener('change', () => run(() => setMode([s.id], mode.value))); controls.append(el('label', 'On save'), mode); container.append(controls);
  const tabs = el('nav', null, 'tabs'); tabs.setAttribute('aria-label', 'Study detail views'); for (const value of ['overview','problems','activity']) { const b = button(human(value[0].toUpperCase() + value.slice(1)), () => { tab = value; renderDetail(); }); if (tab === value) b.className = 'active'; b.setAttribute('aria-current', tab === value ? 'page' : 'false'); tabs.append(b); } container.append(tabs);
  if (s.status === 'unknown') container.append(el('p', 'Upload outcome unknown. Automatic writes are blocked until the server state is reconciled. Resume checks the recorded outcome; it does not blindly replay the upload.', 'notice'));
  if (tab === 'overview') { container.append(el('p', s.stale ? 'Source files changed. Earlier validation is no longer current.' : `Validation: ${human(s.status || 'not run')}.`, 'muted')); if (s.attribution) container.append(el('p', `Contributor attribution: ${typeof s.attribution === 'string' ? s.attribution : JSON.stringify(s.attribution)}`, 'small muted')); const files = el('ul', null, 'files'); for (const f of s.files || []) { const item = el('li'); item.append(el('span', typeof f === 'string' ? f : f.path || f.id, 'grow'), button('Open file', () => openFile(s, f)), button('Reveal', () => openFile(s, f, true))); files.append(item); } container.append(files, el('p', 'Edit in your default applications. Saving triggers the selected action while this local service is running.', 'notice')); }
  if (tab === 'problems') renderProblems(container, s);
  if (tab === 'activity') { const jobsForStudy = state.jobs.filter(j => j.study_id === s.id); if (!jobsForStudy.length) container.append(el('p', 'No activity recorded for this study.', 'muted')); for (const j of jobsForStudy.slice().reverse()) container.append(jobNode(j)); }
}
function renderProblems(container, study) {
  const problems = study.problems || [], filters = el('div', null, 'problem-filter'), severity = el('select'), search = el('input'), list = el('div'); severity.setAttribute('aria-label','Filter problems by severity'); for (const value of ['all','error','warning']) option(severity,value,value === 'all' ? 'All severities' : human(value)); search.type = 'search'; search.placeholder = 'Filter file or issue code…'; search.setAttribute('aria-label','Filter problems by file or issue code'); filters.append(severity,search); container.append(filters,list);
  const draw = () => { list.replaceChildren(); const matched = problems.filter(p => (severity.value === 'all' || (p.severity || 'error') === severity.value) && `${p.code || ''} ${locationText(p)}`.toLowerCase().includes(search.value.toLowerCase())); for (const p of matched) { const card = el('article', null, `problem ${p.severity === 'warning' ? 'warning' : ''}`); card.append(badge(human(p.severity || 'error'), 'invalid'), el('h3', p.title || p.message || p.code || 'Validation problem')); if (p.message && p.title) card.append(el('p', p.message)); card.append(el('span',locationText(p),'location')); if (p.actual != null) card.append(el('p', `Found: ${JSON.stringify(p.actual)}`, 'small')); if (p.expected && Object.keys(p.expected).length) card.append(el('p', `Expected: ${typeof p.expected === 'string' ? p.expected : JSON.stringify(p.expected)}`, 'small')); if (p.hint || p.suggestion) card.append(el('p', p.hint || p.suggestion, 'small muted')); for (const suggestion of p.suggestions || []) card.append(el('p', suggestion.message, 'small muted')); const actions = el('div', null, 'actions'), file = p.location?.file || p.location?.file_name || p.source?.file || p.file; if (file) actions.append(button('Open file', () => openFile(study,file), 'primary'),button('Reveal in folder', () => openFile(study,file,true))); actions.append(button('Copy location', async () => { await navigator.clipboard.writeText(locationText(p)); notify('Source location copied.'); })); card.append(actions); const locations = p.related_sources || p.related_locations || []; if (locations.length) { const related = el('details'); related.append(el('summary', `${locations.length} related locations`)); for (const location of locations) related.append(el('p', [location.label, locationText({location: location.source || location})].filter(Boolean).join(' · '), 'small')); card.append(related); } list.append(card); } if (!matched.length) list.append(el('p', problems.length ? 'No problems match these filters.' : study.status === 'valid' ? 'No validation problems in the current report.' : 'No diagnostics available. Validate this study to produce a report.', 'empty')); };
  severity.addEventListener('change',draw); search.addEventListener('input',draw); draw(); if (study.report_incomplete || study.truncated) container.append(el('p','This report is incomplete. Additional problems may remain.','notice')); if (study.report_id) container.append(reportLink(study.report_id));
}
function reportLink(id) { const link = el('a','Download JSON report'); link.href = `/local/reports/${encodeURIComponent(id)}`; link.download = `pkdb-report-${id}.json`; return link; }
function jobNode(j) { const node = el('div', null, 'job'), text = el('div', null, 'grow'), study = state.studies.find(s => s.id === j.study_id); text.append(el('strong',`${human(j.action)} · ${study?.name || j.study_id || 'Workspace'}`), el('div', [j.stage, j.message, j.created_at ? new Date(j.created_at).toLocaleString() : ''].filter(Boolean).join(' · '), 'small muted')); node.append(text,badge(human(j.status),j.status)); if (j.report_id) node.append(reportLink(j.report_id)); if (j.status === 'queued') node.append(button('Cancel queued job', () => mutate('/local/jobs/cancel', {ids:[j.id]}, 'Queued job canceled.'))); if (j.status === 'unknown' || j.persistence === 'unknown') node.append(button('Review unknown outcome', () => reviewRetry(j))); return node; }
function reviewRetry(job) {
  const study = state.studies.find(s => s.id === job.study_id);
  if (!study) throw new Error('This study is outside the current workspace. Reopen its workspace to reconcile the upload.');
  pendingRetry = study.id;
  $('retry-acknowledge').checked = false;
  $('retry-context').textContent = `${study.name || study.sid || study.id} · Previous target: ${job.endpoint || 'not recorded'}. Retry target: ${state.endpoint || 'not configured'}.`;
  $('retry-link').replaceChildren();
  if (job.endpoint && study.sid) {
    const link = safeLink(`${job.endpoint.replace(/\/$/, '')}/api/v2/studies/${encodeURIComponent(study.sid)}/publication`, 'Inspect publication state on the previous server');
    if (link) $('retry-link').append(link);
  }
  $('retry-link').append(el('p', 'The server link may require its own sign-in. Resume suspended work first to attempt reconciliation with your configured API key.', 'small muted'));
  $('retry-dialog').showModal();
}
function renderJobs() { $('jobs').replaceChildren(); if (!state.jobs.length) $('jobs').append(el('p','No jobs yet. Save a file or select studies to validate.','empty')); for (const j of state.jobs.slice(-12).reverse()) $('jobs').append(jobNode(j)); }
async function jobs(ids, action) { await mutate('/local/jobs', {ids,action}, `${ids.length} ${action === 'validate' ? 'validation' : 'upload'} job(s) queued.`); }
function reviewUpload(ids, mode = false) { if (state.offline) throw new Error('Turn off offline mode before enabling uploads.'); pendingUpload = {ids:[...ids],mode}; $('upload-title').textContent = mode ? 'Enable upload on save' : 'Review upload'; $('upload-context').textContent = `Target: ${state.endpoint || 'not configured'} · PK-DB: ${state.account || 'identity not verified'}. ${ids.length} selected ${ids.length === 1 ? 'study' : 'studies'}.`; $('upload-list').replaceChildren(); for (const id of ids) { const s = state.studies.find(s => s.id === id); $('upload-list').append(el('li', `${s?.name || id} · remote state ${s?.publication?.state || 'unknown'}`)); } $('confirm-upload').textContent = mode ? 'Enable for these studies' : 'Validate and upload'; if (mode) $('upload-context').append(document.createTextNode(' Future saved changes will validate and upload automatically to this target.')); $('upload-dialog').showModal(); }
async function setMode(ids, mode) { if (mode === 'upload') return reviewUpload(ids, true); await mutate('/local/mode',{ids,mode},`On save: ${mode} for ${ids.length} study/studies.`); }
async function refresh(force = false) { if (busy) return; busy = true; try { const data = await api('/local/state'); const next = JSON.stringify(data); state = {...data,studies:data.studies || [],jobs:data.jobs || []}; if (force || next !== signature) { signature = next; render(); } } finally { busy = false; } }
$('user-search').addEventListener('input',renderUsers);
$('issue-state').addEventListener('change',renderStudies);
$('github-user').addEventListener('change', () => run(async () => { view = $('github-user').value ? 'assigned' : 'all'; await mutate('/local/settings',{github_user:$('github-user').value}); }));
for (const id of ['study-search','scope']) $(id).addEventListener(id === 'scope' ? 'change' : 'input',renderStudies);
document.querySelectorAll('[data-view]').forEach(n => n.addEventListener('click', () => { view = n.dataset.view; if (view === 'contributed') { const name = window.prompt('Filter local contributor attribution by username or name:', $('view-description').dataset.contributor || ''); if (name === null) return; $('view-description').dataset.contributor = name; } renderStudies(); }));
$('select-all').addEventListener('change', () => { selected = $('select-all').checked ? new Set(visibleStudies().map(s => s.id)) : new Set(); renderStudies(); });
$('validate').addEventListener('click', () => run(() => jobs([...selected],'validate')));
$('upload').addEventListener('click', () => run(() => reviewUpload([...selected])));
$('apply-mode').addEventListener('click', () => run(() => setMode([...selected],$('batch-mode').value)));
$('clear-history').addEventListener('click', () => run(() => mutate('/local/history/clear', {}, 'Finished history cleared; active and unknown jobs retained.')));
$('retry-form').addEventListener('submit', event => { event.preventDefault(); run(async () => { if (!pendingRetry || !$('retry-acknowledge').checked) return; await mutate('/local/retry', {id:pendingRetry,acknowledge_unknown:true}, 'Explicit retry queued.'); pendingRetry = null; $('retry-dialog').close(); }); });
$('pause').addEventListener('click', () => run(() => mutate('/local/pause',{paused:!state.paused})));
$('resume').addEventListener('click', () => run(() => mutate('/local/resume',selected.size ? {ids:[...selected]} : {},'Requested reconciliation and resume.')));
$('refresh-files').addEventListener('click', () => run(() => mutate('/local/workspace',{path:state.workspace},'Source files refreshed.')));
$('refresh-assignments').addEventListener('click', () => run(() => mutate('/local/assignments/refresh',{},'Assignments refreshed.')));
$('workspace-open').addEventListener('click', () => { $('workspace-path').value = state.workspace || ''; $('workspace-dialog').showModal(); });
$('settings-open').addEventListener('click', () => { $('settings-endpoint').value = state.endpoint || ''; $('settings-key').value = ''; $('settings-offline').checked = !!state.offline; $('settings-dialog').showModal(); });
document.querySelectorAll('[data-close]').forEach(n => n.addEventListener('click', () => { $(n.dataset.close).close(); $('settings-key').value = ''; }));
$('workspace-form').addEventListener('submit', event => { event.preventDefault(); run(async () => { await mutate('/local/workspace',{path:$('workspace-path').value},'Workspace opened.'); selected.clear(); current = ''; $('study-detail').hidden = true; $('workspace-dialog').close(); render(); }); });
$('settings-form').addEventListener('submit', event => { event.preventDefault(); run(async () => { const settings = {endpoint:$('settings-endpoint').value,offline:$('settings-offline').checked}; if ($('settings-key').value) settings.api_key = $('settings-key').value; $('settings-key').value = ''; await mutate('/local/settings',settings,'Connection settings updated.'); $('settings-dialog').close(); }); });
$('settings-dialog').addEventListener('close', () => { $('settings-key').value = ''; });
$('upload-form').addEventListener('submit', event => { event.preventDefault(); run(async () => { if (!pendingUpload) return; const {ids,mode} = pendingUpload; $('upload-dialog').close(); pendingUpload = null; if (mode) await mutate('/local/mode',{ids,mode:'upload'},'Upload on save enabled for the reviewed selection.'); else await jobs(ids,'upload'); }); });
async function start() { const fragment = new URLSearchParams(location.hash.slice(1)); const token = fragment.get('token') || (location.hash.length > 1 && !location.hash.includes('=') ? location.hash.slice(1) : ''); if (token) { history.replaceState(null,'',location.pathname + location.search); await api('/local/session',{token}); } await refresh(true); setInterval(() => run(() => refresh()),1500); }
run(start);
