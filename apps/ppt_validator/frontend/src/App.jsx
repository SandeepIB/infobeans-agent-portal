import { useState, useRef, useCallback, useEffect } from 'react'
import './App.css'

const AGENTS = [
  { id: 'branding',          name: 'Branding',         desc: 'Fonts, colors, logo compliance',        type: 'rule' },
  { id: 'template',          name: 'Template',         desc: 'Layout and slide structure checks',      type: 'rule' },
  { id: 'visual_quality',    name: 'Visual Quality',   desc: 'Layout density, readability & table design', type: 'rule' },
  { id: 'content',           name: 'Content Quality',  desc: 'Clarity, depth, and deck consistency',   type: 'llm'  },
  { id: 'story',             name: 'Story Arc',        desc: 'Narrative flow and logical structure',    type: 'llm'  },
  { id: 'customer_focus',    name: 'Customer Focus',   desc: 'Audience relevance and messaging',       type: 'llm'  },
  { id: 'proposal_context',  name: 'Proposal Context', desc: 'Alignment to deal and scope context',    type: 'llm'  },
  { id: 'cio_lens',          name: 'CIO Lens',         desc: 'Executive and strategic readiness',      type: 'llm'  },
  { id: 'critic',            name: 'Critic',           desc: 'Final adversarial quality review',       type: 'llm'  },
]

function scoreClass(score) {
  if (score >= 80) return 'pass'
  if (score >= 60) return 'warn'
  return 'fail'
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function ScoreBar({ score }) {
  const cls = scoreClass(score)
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-bg">
        <div className={`score-bar-fill ${cls}`} style={{ width: `${score}%` }} />
      </div>
      <span className="score-bar-num">{score}</span>
    </div>
  )
}

function formatSummaryBullets(summary) {
  if (!summary || summary === '—') return '—'
  const raw = String(summary).trim()
  let lines = raw.split(/\r?\n/).map(l => l.replace(/^[•\-\*\s]+/, '').trim()).filter(Boolean)
  if (lines.length <= 1) {
    lines = raw.split(/(?<=\.)\s+(?=[A-Z0-9])/).map(s => s.trim()).filter(Boolean)
  }
  if (lines.length > 1) {
    return (
      <ul className="summary-bullet-list">
        {lines.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    )
  }
  return raw
}

function formatPromptCode(text) {
  if (!text) return ''
  let formatted = String(text)
  // Expand inline numbered lists like "(1) ... (2) ..." or "1) ... 2) ..." onto newlines with bullet points
  formatted = formatted.replace(/(?:\s+|^)(\(\d+\)|\d+\))\s+/g, '\n  • $1 ')
  // Ensure "Evaluate:" or "Evaluate key visual elements:" is followed by a clean line break
  formatted = formatted.replace(/(Evaluate[^:\n]*:)\s*/gi, '$1\n')
  return formatted.trim()
}

export default function App() {
  const fileRef = useRef(null)
  const [file, setFile]                   = useState(null)
  const [dragging, setDragging]           = useState(false)
  const [context, setContext]             = useState('')
  const [selectedAgents, setSelectedAgents] = useState(() => new Set(AGENTS.map(a => a.id)))
  const [loading, setLoading]             = useState(false)
  const [error, setError]                 = useState('')
  const [result, setResult]               = useState(null)
  const [activeTab, setActiveTab]         = useState('agents')
  const [history, setHistory]             = useState([])
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [agentFilter, setAgentFilter]       = useState('ALL')
  const [groupBy, setGroupBy]               = useState('slide')
  const [inspectAgent, setInspectAgent]     = useState(null)
  const [promptData, setPromptData]         = useState(null)
  const [promptLoading, setPromptLoading]   = useState(false)
  const [copiedField, setCopiedField]       = useState(null)

  // Load history on mount
  useEffect(() => { loadHistory() }, [])

  async function handleInspectPrompt(e, agent) {
    e.preventDefault()
    e.stopPropagation()
    setInspectAgent(agent)
    setPromptData(null)
    setCopiedField(null)
    if (agent.type === 'rule') return

    setPromptLoading(true)
    try {
      const res = await fetch(`/api/v2/prompts/${agent.id}/active`)
      if (res.ok) {
        const data = await res.json()
        setPromptData(data)
      }
    } catch {
      /* ignore */
    } finally {
      setPromptLoading(false)
    }
  }

  // ── File handling ──────────────────────────────────────────────────────────
  function handleFile(f) {
    if (!f || !f.name.toLowerCase().endsWith('.pptx')) {
      setError('Please select a .pptx file.')
      return
    }
    setFile(f)
    setError('')
  }

  const onDrop = useCallback(e => {
    e.preventDefault(); setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }, [])

  // ── Agent toggle ────────────────────────────────────────────────────────────
  function toggleAgent(id) {
    setSelectedAgents(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (selectedAgents.size === AGENTS.length) {
      setSelectedAgents(new Set())
    } else {
      setSelectedAgents(new Set(AGENTS.map(a => a.id)))
    }
  }

  // ── Submit ─────────────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!file) return
    if (selectedAgents.size === 0) { setError('Select at least one agent to run.'); return }

    setLoading(true); setError(''); setResult(null)

    const profile = {
      review_profile: 'customer_presentation',
      agents: AGENTS.map(a => ({ id: a.id, enabled: selectedAgents.has(a.id) })),
    }
    const fd = new FormData()
    fd.append('file', file)
    fd.append('profile', JSON.stringify(profile))
    if (context.trim()) fd.append('proposal_context', context.trim())

    try {
      const res = await fetch('/api/v2/review', { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Server error ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
      setActiveTab('agents')
      loadHistory()
    } catch (e) {
      if (e.message.includes('Failed to fetch') || e.name === 'TypeError') {
        // Network timeout / connection drop recovery: check if backend completed run
        setTimeout(async () => {
          const rows = await loadHistory()
          if (rows && rows.length > 0) {
            const latest = rows[0]
            if (latest && (latest.filename === file.name || (new Date() - new Date(latest.started_at)) < 180000)) {
              loadRun(latest.run_id)
              setError('')
              return
            }
          }
          setError('Network response delayed. Please check Review History below for the completed report.')
        }, 1500)
      } else {
        setError(e.message)
      }
    } finally {
      setLoading(false)
    }
  }

  async function loadHistory() {
    try {
      const rows = await fetch('/api/v2/review').then(r => r.json())
      setHistory(rows || [])
      return rows || []
    } catch { return [] }
  }

  async function loadRun(runId) {
    try {
      const data = await fetch(`/api/v2/review/${runId}`).then(r => r.json())
      if (data.agent_results) {
        setResult(data)
        setActiveTab('agents')
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
    } catch { /* ignore */ }
  }

  // ── Derived result data ────────────────────────────────────────────────────
  const agentResults   = result?.agent_results ?? []
  const allFindings    = agentResults.flatMap(a => (a.findings ?? []).map(f => ({ ...f, agent: a.agent_id })))
  const completedCount = agentResults.filter(a => a.status === 'completed').length
  const failedCount    = agentResults.filter(a => a.status === 'failed').length
  const criticalCount  = allFindings.filter(f => f.severity === 'CRITICAL').length
  const highCount      = allFindings.filter(f => f.severity === 'HIGH').length

  const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

  function slideNum(f) {
    const n = parseInt(f.slide)
    return isNaN(n) ? Infinity : n
  }

  const filteredFindings = allFindings
    .filter(f => {
      if (severityFilter !== 'ALL' && f.severity !== severityFilter) return false
      if (agentFilter !== 'ALL' && f.agent !== agentFilter) return false
      return true
    })
    .sort((a, b) => {
      if (groupBy === 'agent') {
        if (a.agent < b.agent) return -1
        if (a.agent > b.agent) return 1
        return (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4)
      }
      const sa = slideNum(a), sb = slideNum(b)
      if (sa !== sb) return sa - sb
      return (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4)
    })

  function groupFindings(findings) {
    if (groupBy === 'none') return [{ key: null, items: findings }]
    const groups = []
    let currentKey, currentGroup
    for (const f of findings) {
      let key
      if (groupBy === 'slide') {
        key = f.slide ? `Slide ${f.slide}` : 'Deck Level'
      } else {
        const agentDef = AGENTS.find(x => x.id === f.agent)
        key = agentDef?.name ?? f.agent
      }
      if (key !== currentKey) {
        currentGroup = { key, items: [] }
        groups.push(currentGroup)
        currentKey = key
      }
      currentGroup.items.push(f)
    }
    return groups
  }

  const scoreCls  = result ? scoreClass(result.score ?? 0) : 'pass'
  const scoreLabel = scoreCls === 'pass' ? 'READY' : scoreCls === 'warn' ? 'REVIEW' : 'BLOCKED'

  return (
    <>
      {/* Nav */}
      <nav className="ib-nav">
        <div className="nav-logo">
          <div className="nav-logo-box">IB</div>
          InfoBeans PPT Review Platform
        </div>
        <span className="nav-badge">AI Review</span>
      </nav>

      {/* Hero */}
      <div className="ib-hero">
        <div className="hero-eyebrow">★ Agentic Review Platform</div>
        <h1>Review your deck with <span>AI-powered</span> agents</h1>
        <p>Upload any .pptx file. Run specialized agents for brand compliance, content quality, narrative flow, and CIO-readiness.</p>
      </div>

      <main className="ib-main">

        {/* Upload card */}
        <div className="card">
          <div className="card-label">Upload Deck</div>

          <div
            className={`drop-zone${dragging ? ' over' : ''}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input
              ref={fileRef} type="file" accept=".pptx" style={{ display: 'none' }}
              onChange={e => handleFile(e.target.files[0])}
            />
            <div className="drop-icon">📊</div>
            <p>Drag &amp; drop a <strong>.pptx</strong> file here<br />or <strong>click to browse</strong></p>
          </div>

          {file && (
            <div className="file-name">
              📎&nbsp;&nbsp;{file.name}&nbsp;&nbsp;({(file.size / 1024 / 1024).toFixed(1)} MB)
            </div>
          )}

          {/* Proposal context */}
          <div className="form-row">
            <label htmlFor="ctx">
              Proposal context&nbsp;<span className="opt">(optional — helps AI agents)</span>
            </label>
            <textarea
              id="ctx"
              placeholder="e.g. Sales pitch for Five Star Alliance, covering MCP integration, 6 tools, and demo flow."
              value={context}
              onChange={e => setContext(e.target.value)}
            />
            <small>Describe the purpose, audience, and topic. Used only for AI content agents.</small>
          </div>

          {/* Agent selection */}
          <div className="agents-section">
            <div className="agents-header">
              <span className="agents-header-label">
                Review Agents&nbsp;
                <span style={{ color: 'var(--ib-mid)', fontWeight: 400 }}>
                  ({selectedAgents.size} of {AGENTS.length} selected)
                </span>
              </span>
              <button className="toggle-all-btn" onClick={toggleAll}>
                {selectedAgents.size === AGENTS.length ? 'Deselect all' : 'Select all'}
              </button>
            </div>
            <div className="agents-grid">
              {AGENTS.map(agent => (
                <label key={agent.id} className="agent-check">
                  <input
                    type="checkbox"
                    checked={selectedAgents.has(agent.id)}
                    onChange={() => toggleAgent(agent.id)}
                  />
                  <div className="agent-check-body">
                    <span className="agent-check-name">{agent.name}</span>
                    <span className="agent-check-desc">{agent.desc}</span>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
                      <span className={`agent-type-tag ${agent.type}`}>
                        {agent.type === 'rule' ? 'Rule-based' : 'LLM'}
                      </span>
                      <button
                        className="view-prompt-btn"
                        onClick={(e) => handleInspectPrompt(e, agent)}
                        title={agent.type === 'rule' ? `View ${agent.name} inspection rules` : `View ${agent.name} default prompt & instructions`}
                      >
                        {agent.type === 'rule' ? '👁 Rules' : '👁 Prompt'}
                      </button>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && <div className="error-banner">⚠ {error}</div>}

          {/* Submit */}
          <div className="submit-row">
            {file && !loading && (
              <button className="submit-btn" onClick={handleSubmit}>
                Run Review
              </button>
            )}
            {loading && (
              <div className="spinner">
                <div className="spin-dot" /><div className="spin-dot" /><div className="spin-dot" />
                <span>Reviewing…</span>
              </div>
            )}
          </div>
        </div>

        {/* Result */}
        {result && (
          <>
            {/* Score banner */}
            <div className="score-banner">
              <div className={`score-circle ${scoreCls}`}>
                <span className="pct">{result.score ?? 0}</span>
                <span className="lbl">{scoreLabel}</span>
              </div>
              <div className="score-meta">
                <h3>{file?.name} — {agentResults.length} agent{agentResults.length !== 1 ? 's' : ''} run</h3>
                <p>
                  {completedCount} completed · {failedCount} failed ·{' '}
                  {allFindings.length} finding{allFindings.length !== 1 ? 's' : ''} ·{' '}
                  {criticalCount} critical · {highCount} high
                </p>
              </div>
              {result.run_id && (
                <a
                  className="pdf-btn"
                  href={`/api/v2/review/${result.run_id}/report.pdf`}
                  download={`review-${result.run_id}.pdf`}
                >
                  ⬇ Download PDF
                </a>
              )}
            </div>

            {/* Pills */}
            <div className="pills">
              {criticalCount > 0 && <span className="pill fail">🔴 {criticalCount} Critical</span>}
              {highCount > 0     && <span className="pill fail">🟠 {highCount} High</span>}
              {completedCount > 0 && <span className="pill ok">✓ {completedCount} Agents Passed</span>}
              {failedCount > 0   && <span className="pill warn">⚠ {failedCount} Agent{failedCount > 1 ? 's' : ''} Failed</span>}
              {allFindings.length === 0 && <span className="pill ok">✓ No findings</span>}
              {(() => {
                const storyRes = agentResults.find(a => a.agent_id === 'story')
                const fmt = storyRes?.metadata?.delivery_format || (storyRes?.summary?.includes('Email') ? 'Email Leave-Behind' : 'In-Person Presentation')
                const mins = storyRes?.metadata?.estimated_minutes
                return (
                  <>
                    <span className="pill info" style={{ background: '#eef2ff', color: '#4338ca', border: '1px solid #c7d2fe' }}>
                      🎤 Delivery: {fmt}
                    </span>
                    {mins && (
                      <span className="pill info" style={{ background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0' }}>
                        ⏱️ Est. Duration: ~{mins} mins
                      </span>
                    )}
                  </>
                )
              })()}
            </div>

            {/* Tabs */}
            <div className="tabs-wrap">
              <div className="tabs">
                {[
                  { id: 'agents',   label: `Agent Results (${agentResults.length})` },
                  { id: 'findings', label: `Findings (${allFindings.length})` },
                ].map(t => (
                  <div
                    key={t.id}
                    className={`tab${activeTab === t.id ? ' active' : ''}`}
                    onClick={() => setActiveTab(t.id)}
                  >
                    {t.label}
                  </div>
                ))}
              </div>

              {/* Agent results tab */}
              {activeTab === 'agents' && (
                <div className="tab-panel">
                  <div className="tbl-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th style={{ width: '20%' }}>Agent</th>
                          <th style={{ width: '12%' }}>Status</th>
                          <th style={{ width: '16%' }}>Score</th>
                          <th style={{ width: '10%' }}>Findings</th>
                          <th style={{ width: '42%' }}>Summary</th>
                        </tr>
                      </thead>
                      <tbody>
                        {agentResults.map(a => {
                          const agentDef = AGENTS.find(x => x.id === a.agent_id)
                          const findings = a.findings ?? []
                          return (
                            <tr key={a.agent_id}>
                              <td>
                                <strong>{agentDef?.name ?? a.agent_id}</strong>
                                {agentDef && (
                                  <span className={`agent-type-tag ${agentDef.type}`} style={{ marginLeft: 6 }}>
                                    {agentDef.type === 'rule' ? 'Rule' : 'LLM'}
                                  </span>
                                )}
                              </td>
                              <td><span className={`badge ${a.status}`}>{a.status}</span></td>
                              <td>
                                {a.status === 'completed'
                                  ? <ScoreBar score={a.score ?? 0} />
                                  : <span style={{ color: 'var(--ib-mid)', fontSize: '0.78rem' }}>—</span>
                                }
                              </td>
                              <td style={{ fontWeight: 700, color: findings.length > 0 ? 'var(--ib-brand-red)' : 'var(--ib-green)' }}>
                                {findings.length}
                              </td>
                              <td className="summary-cell">
                                {formatSummaryBullets(a.summary)}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Findings tab */}
              {activeTab === 'findings' && (
                <div className="tab-panel">
                  {allFindings.length === 0 ? (
                    <div className="no-issues">
                      ✓ No findings across all agents
                      <small>All selected agents ran clean.</small>
                    </div>
                  ) : (
                    <>
                      {/* Findings Filters */}
                      <div className="findings-filters">
                        <div className="filter-group">
                          <label>Severity:</label>
                          <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}>
                            <option value="ALL">All Severities ({allFindings.length})</option>
                            <option value="CRITICAL">Critical ({criticalCount})</option>
                            <option value="HIGH">High ({highCount})</option>
                            <option value="MEDIUM">Medium ({allFindings.filter(f => f.severity === 'MEDIUM').length})</option>
                            <option value="LOW">Low ({allFindings.filter(f => f.severity === 'LOW').length})</option>
                          </select>
                        </div>
                        <div className="filter-group">
                          <label>Agent:</label>
                          <select value={agentFilter} onChange={e => setAgentFilter(e.target.value)}>
                            <option value="ALL">All Agents</option>
                            {Array.from(new Set(allFindings.map(f => f.agent))).map(aid => {
                              const agentDef = AGENTS.find(x => x.id === aid)
                              return <option key={aid} value={aid}>{agentDef?.name ?? aid}</option>
                            })}
                          </select>
                        </div>
                        <div className="filter-group">
                          <label>Group by:</label>
                          <select value={groupBy} onChange={e => setGroupBy(e.target.value)}>
                            <option value="slide">Slide</option>
                            <option value="agent">Agent</option>
                            <option value="none">None (flat)</option>
                          </select>
                        </div>
                      </div>

                      {/* Findings Card List */}
                      {filteredFindings.length === 0 ? (
                        <div className="no-issues" style={{ color: 'var(--ib-mid)' }}>
                          No findings match the selected filters.
                        </div>
                      ) : (
                        <div className="findings-list">
                          {groupFindings(filteredFindings).map((group, gi) => (
                            <div key={gi}>
                              {group.key && (
                                <div className="findings-group-header">
                                  <span className="findings-group-label">{group.key}</span>
                                  <span className="findings-group-count">{group.items.length} finding{group.items.length !== 1 ? 's' : ''}</span>
                                </div>
                              )}
                              {group.items.map((f, i) => {
                                const agentDef = AGENTS.find(x => x.id === f.agent)
                                return (
                                  <div key={i} className={`finding-card severity-${f.severity || 'LOW'}`}>
                                    <div className="finding-card-header">
                                      <div className="finding-badges">
                                        {groupBy !== 'slide' && (
                                          <span className="slide-tag">
                                            {f.slide ? `Slide ${f.slide}` : 'Deck Level'}
                                          </span>
                                        )}
                                        <span className={`badge ${f.severity}`}>{f.severity}</span>
                                        {groupBy !== 'agent' && (
                                          <span className="agent-tag-sm">
                                            {agentDef?.name ?? f.agent}
                                          </span>
                                        )}
                                      </div>
                                      <span className={`badge ${f.action_type}`}>
                                        {f.action_type === 'AUTO_FIX' ? '⚡ Auto-fix' : f.action_type === 'HUMAN_APPROVAL' ? '👤 Approval' : '💡 Recommend'}
                                      </span>
                                    </div>

                                    <div className="finding-title">{f.title}</div>
                                    <div className="finding-desc">{f.description}</div>

                                    {f.recommendation && (
                                      <div className="finding-rec-box">
                                        <div className="rec-label">💡 Recommendation</div>
                                        <div className="rec-content">{formatSummaryBullets(f.recommendation)}</div>
                                      </div>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </>
        )}

        {/* History — always shown, loads on mount */}
        <div className="card" style={{ marginTop: '2rem' }}>
          <div className="card-label">Review History</div>
          {history.length === 0 ? (
            <div className="no-issues" style={{ color: 'var(--ib-mid)' }}>
              No reviews yet
              <small>Upload a .pptx file above to run your first review.</small>
            </div>
          ) : (
            <div className="tbl-wrap">
              <table>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Status</th>
                    <th>Quality Gate</th>
                    <th>Score</th>
                    <th>Started</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(r => {
                    const isFinished = r.status === 'completed' || ['ready', 'review', 'blocked'].includes(r.status)
                    const isFailed   = r.status === 'failed'
                    const gate       = r.quality_gate || (['ready', 'review', 'blocked'].includes(r.status) ? r.status : null)
                    return (
                      <tr key={r.run_id}>
                        <td style={{ fontWeight: 600, maxWidth: 200, wordBreak: 'break-word' }}>
                          {r.filename ?? r.run_id}
                        </td>
                        <td>
                          <span className={`badge ${isFailed ? 'failed' : isFinished ? 'completed' : 'info'}`}>
                            {isFailed ? 'FAILED' : isFinished ? 'COMPLETED' : 'RUNNING'}
                          </span>
                        </td>
                        <td>
                          {gate === 'ready'   && <span className="badge ready">READY</span>}
                          {gate === 'review'  && <span className="badge review">REVIEW</span>}
                          {gate === 'blocked' && <span className="badge blocked">BLOCKED</span>}
                          {!gate && <span style={{ color: 'var(--ib-mid)', fontSize: '0.78rem' }}>—</span>}
                        </td>
                        <td>
                          {r.score != null
                            ? <ScoreBar score={r.score} />
                            : <span style={{ color: 'var(--ib-mid)', fontSize: '0.78rem' }}>—</span>
                          }
                        </td>
                        <td style={{ fontSize: '0.76rem', color: 'var(--ib-mid)', whiteSpace: 'nowrap' }}>
                          {r.started_at ? new Date(r.started_at).toLocaleString() : '—'}
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <button
                              className="toggle-all-btn"
                              onClick={() => loadRun(r.run_id)}
                              title="Load this run's results"
                            >
                              View →
                            </button>
                            {isFinished && (
                              <a
                                className="pdf-btn-sm"
                                href={`/api/v2/review/${r.run_id}/report.pdf`}
                                download={`review-${r.run_id}.pdf`}
                                title="Download PDF report"
                              >
                                PDF
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </main>

      <footer className="ib-footer">
        <strong>InfoBeans</strong> Agentic PPT Review Platform &nbsp;·&nbsp;
        python-pptx · FastAPI · Claude AI
      </footer>

      {/* ── Prompt Inspector Modal ── */}
      {inspectAgent && (
        <div className="modal-overlay" onClick={() => setInspectAgent(null)}>
          <div className="modal-content prompt-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>{inspectAgent.type === 'rule' ? `${inspectAgent.name} Agent Rules` : `${inspectAgent.name} Agent Prompt`}</h3>
                <span className={`agent-type-tag ${inspectAgent.type}`}>
                  {inspectAgent.type === 'rule' ? 'Deterministic Python Inspection' : 'Active LLM Prompt v1.1.0'}
                </span>
              </div>
              <button className="modal-close" onClick={() => setInspectAgent(null)}>✕</button>
            </div>

            <div className="modal-body">
              {inspectAgent.type === 'rule' ? (
                <div className="prompt-block">
                  <div className="prompt-block-header">
                    <span className="prompt-block-title">Deterministic Python Rule Inspection</span>
                  </div>
                  <p className="rule-desc">
                    {inspectAgent.id === 'branding' ? (
                      <>
                        Evaluates slides programmatically against rules configured in <code>rules.yaml</code>:
                        <ul className="rule-bullet-list">
                          <li><strong>1. Aspect Ratio / Size:</strong> Enforces 16:9 widescreen format (10 in × 5.625 in / 25.4 × 14.29 cm). Flags 4:3 as 🔴 BLOCKER.</li>
                          <li><strong>2. Primary Typeface:</strong> Mandates <strong>Lexend</strong> family (Thin, Regular, SemiBold). Flags non-brand fonts as 🔴 BLOCKER.</li>
                          <li><strong>3. Italics Enforcement:</strong> Restricts italics to <strong>Verdana</strong> where required. Flags Lexend italics as 🟠 SHOULD-FIX.</li>
                          <li><strong>4. Default Page Background:</strong> Validates Light Cream <code>#FFF9ED</code> default background.</li>
                          <li><strong>5. Color Palette:</strong> Enforces 11 brand hex codes (#EA1B3D, #373742, #676775, #E6E6ED, #FFF9ED, #FFF3D4, #FFFFFF, #FFD0D8, #EB4C5E, #AA142D, #7C2235). Flags pure black (#000000) or off-palette text as 🟠 SHOULD-FIX.</li>
                          <li><strong>6. Logo Placement & Size:</strong> Uses bounding-box candidate distance matching to verify InfoBeans brandmark in bottom-right corner. Missing logo → 🔴 HIGH.</li>
                          <li><strong>7. Slide Pagination:</strong> Validates bottom-left sequential page numbers (8–9pt, Lexend, Medium Gray #676775).</li>
                          <li><strong>8. Heading Casing:</strong> Enforces sentence case on headlines (first word capitalized; no ALL-CAPS or Title Case).</li>
                          <li><strong>9. Eyebrow Headers:</strong> Validates eyebrow header casing (ALL CAPS / UPPERCASE) and positioning (must sit above main title).</li>
                          <li><strong>10. Leftover Template Placeholders:</strong> Scans for unfinished string patterns ("Add title here", "Add copy here", "Lorem ipsum", "DO NOT USE", "Example Slide"). 🔴 BLOCKER.</li>
                          <li><strong>11. Source Footnote Citations:</strong> Ensures slides containing statistics, percentages, or financial metrics carry a "Source: ..." footnote.</li>
                          <li><strong>12. Brand Name Capitalization:</strong> Enforces exact capitalization "InfoBeans" (capital I and B).</li>
                        </ul>
                      </>
                    ) : (
                      <>
                        Evaluates presentation slide structure and layout rules programmatically:
                        <ul className="rule-bullet-list">
                          <li><strong>1. Layout Hierarchy:</strong> Verifies 16:9 widescreen layout dimensions and master slide inheritance.</li>
                          <li><strong>2. Master Template Alignment:</strong> Validates standard slide types against canonical master layouts (Cover, Section Divider, Agenda, Content, Stat, Quote, Testimonial, Case Study, Closing).</li>
                          <li><strong>3. Custom Background Restrictions:</strong> Restricts custom background colors exclusively to section dividers, quotes, and case-study slides. 🔴 BLOCKER on content slides.</li>
                          <li><strong>4. Placeholder Integrity:</strong> Validates title shape placeholder presence and unassigned text shape placement.</li>
                        </ul>
                      </>
                    )}
                  </p>
                  {inspectAgent.id === 'visual_quality' && (
                    <>
                      <p className="rule-desc" style={{ marginTop: '1.2rem' }}>
                        Also performs deterministic <strong>layout density</strong> checks:
                        <ul className="rule-bullet-list">
                          <li><strong>VIS-RULE-001:</strong> Bullet count overload — flags slides with more than 7 bullet points. 🟡 MEDIUM.</li>
                          <li><strong>VIS-RULE-002:</strong> High text density — flags slides exceeding 150 words. 🟡 MEDIUM.</li>
                          <li><strong>VIS-RULE-003:</strong> Low content density — flags non-title slides with fewer than 10 words and no image. 🟢 LOW.</li>
                          <li><strong>VIS-RULE-004:</strong> Missing slide title — every slide must have a headline. 🟡 MEDIUM.</li>
                          <li><strong>VIS-RULE-005:</strong> Excessive font variety — flags decks with more than 3 distinct font families. 🟡 MEDIUM.</li>
                        </ul>
                      </p>
                      <p className="rule-desc" style={{ marginTop: '1.2rem' }}>
                        And <strong>Table Design Guidelines</strong> checks (Rules 1–12 from the Executive Presentation standard):
                      </p>
                      <p className="rule-desc" style={{ fontWeight: 600, marginBottom: '0.3rem', color: 'var(--ib-brand-red)' }}>
                        📐 Page 1 — Structure
                      </p>
                      <p className="rule-desc">
                        <ul className="rule-bullet-list">
                          <li><strong>TBL-RULE-001 (Rule 2 — Column Count Advisory):</strong> Table has 7–8 columns. Acceptable but requires careful design. Ideally limit to 4–6. 🟢 LOW.</li>
                          <li><strong>TBL-RULE-002 (Rule 2 — Column Count Critical):</strong> Table has 9+ columns — reconsider structure. Split into multiple tables, use a chart, or move detail to appendix. 🔴 HIGH.</li>
                          <li><strong>TBL-RULE-003 (Rule 8 — Header Presence):</strong> Table has no visually distinct header row (no bold or filled first row). Headers anchor the table. 🟡 MEDIUM.</li>
                          <li><strong>TBL-RULE-004 (Rule 4 — Content Alignment):</strong> Column data alignment contradicts content type. Text → Left | Numbers (revenue, %, counts) → Right | Signals (status, Yes/No, icons) → Center. 🟡 MEDIUM.</li>
                          <li><strong>TBL-RULE-005 (Rule 5 — Header Alignment):</strong> Column header alignment differs from the data below it. As a default, headers should match their data alignment. 🟢 LOW.</li>
                          <li><strong>TBL-RULE-006 (Rule 11 — Number Format):</strong> A column mixes incompatible number formats (e.g. $2.4M with $1,850,000; or 18% with 18.0%). Standardize within each column. 🟡 MEDIUM.</li>
                          <li><strong>TBL-RULE-010 (Rule 3 — Column Width):</strong> All columns have equal widths — information density is ignored. Give more width to text-heavy columns, less to short fields like Status or Year. 🟢 LOW.</li>
                          <li><strong>TBL-RULE-011 (Rule 8 — Header Verbosity):</strong> One or more column headers exceed 4 words, reading like a sentence rather than a short label. Shorten to 1–4 words. 🟢 LOW.</li>
                        </ul>
                      </p>
                      <p className="rule-desc" style={{ fontWeight: 600, marginBottom: '0.3rem', color: 'var(--ib-brand-red)' }}>
                        🎨 Page 2 — Visual Design &amp; Executive Readability
                      </p>
                      <p className="rule-desc">
                        <ul className="rule-bullet-list">
                          <li><strong>TBL-RULE-007 (Rule 7 — Border Minimalism):</strong> Table has heavy borders on ≥70% of cells — spreadsheet feel. Prefer header separator + subtle horizontal lines + white space. 🟢 LOW.</li>
                          <li><strong>TBL-RULE-008 (Rule 6 — Row Compactness):</strong> Many cells contain 3+ lines of text — fails the 5-second scan test. Keep rows compact; move detail to appendix. 🟡 MEDIUM.</li>
                          <li><strong>TBL-RULE-009 (Rule 9 — Font Readability):</strong> Table uses a non-brand font family. Use the same font as the rest of the deck; don't shrink to fit — fix the table instead. 🟢 LOW.</li>
                          <li><strong>TBL-RULE-012 (Rule 10 — Color Communication):</strong> Table has 4+ distinct cell fill colors — decorative overuse. Color should communicate meaning: Green = On Track, Amber = At Risk, Red = Off Track. Highlight only key information. 🟡 MEDIUM.</li>
                        </ul>
                      </p>
                    </>
                  )}
                </div>
              ) : (
                <>
                  {promptLoading ? (
                    <div className="spinner modal-spinner">
                      <div className="spin-dot" /><div className="spin-dot" /><div className="spin-dot" />
                      <span>Loading active prompt configuration…</span>
                    </div>
                  ) : (
                    <>
                      <div className="prompt-block">
                        <div className="prompt-block-header">
                          <span className="prompt-block-title">System Prompt</span>
                          <button
                            className="copy-btn"
                            onClick={() => {
                              navigator.clipboard.writeText(promptData?.system || '')
                              setCopiedField('system')
                              setTimeout(() => setCopiedField(null), 2000)
                            }}
                          >
                            {copiedField === 'system' ? '✓ Copied' : '📋 Copy'}
                          </button>
                        </div>
                        <pre className="prompt-code">{formatPromptCode(promptData?.system) || 'System prompt configuration'}</pre>
                      </div>

                      <div className="prompt-block">
                        <div className="prompt-block-header">
                          <span className="prompt-block-title">User Prompt Template</span>
                          <button
                            className="copy-btn"
                            onClick={() => {
                              navigator.clipboard.writeText(promptData?.user_template || '')
                              setCopiedField('user_template')
                              setTimeout(() => setCopiedField(null), 2000)
                            }}
                          >
                            {copiedField === 'user_template' ? '✓ Copied' : '📋 Copy'}
                          </button>
                        </div>
                        <pre className="prompt-code">{promptData?.user_template || 'User template configuration'}</pre>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>

            <div className="modal-footer">
              <button className="submit-btn" onClick={() => setInspectAgent(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
