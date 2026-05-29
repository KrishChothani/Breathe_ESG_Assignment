/**
 * src/components/Chatbot/index.jsx
 * ==================================
 * Self-contained BreatheESG Emissions Assistant chat widget.
 *
 * Renders as:
 *   - A fixed floating button (bottom-right corner)
 *   - A slide-in chat panel from the right side of the screen
 *
 * Features:
 *   - Text, table, and chart response types
 *   - Recharts-powered Line / Bar / Donut charts
 *   - Expandable tables (max 8 rows visible, "Show all" button)
 *   - Follow-up question chips after each response
 *   - Starter question chips in empty state
 *   - CSV download for chart/table responses
 *   - Context-aware trigger via window.__chatbot.openWithContext(rowId, source)
 *   - Conversation continuity via sessionStorage UUID
 *   - Loading animation (3-dot pulse)
 *   - Error bubbles with retry option
 *
 * Zero changes to any existing component or layout file.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  LineChart, Line,
  BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import client from '../../api/client'

// ── Constants ────────────────────────────────────────────────────────────────

const STARTER_QUESTIONS = [
  'What are my total Scope 1+2 emissions this FY?',
  'Show me the Scope 2 trend for last 6 months',
  'Which rows are flagged as suspicious right now?',
  "What's our GHG intensity per crore of revenue?",
  'How many audit findings are unresolved?',
  'Which SAP plant contributes most to Scope 1?',
  'Compare this FY vs last FY across all scopes',
  'What utility bills were processed this month?',
]

const CHART_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4']

const CO2_COL_KEYWORDS = ['co2', 'tonne', 'kg', 'emission', 'carbon']

// ── Helpers ──────────────────────────────────────────────────────────────────

function getConversationId() {
  const key = 'breathe_chatbot_conv_id'
  let id = sessionStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem(key, id)
  }
  return id
}

function isCO2Column(colName) {
  return CO2_COL_KEYWORDS.some(kw => colName.toLowerCase().includes(kw))
}

function isNumeric(value) {
  return typeof value === 'number' || (typeof value === 'string' && !isNaN(parseFloat(value)))
}

function formatValue(col, value) {
  if (value === null || value === undefined) return '—'
  if (isCO2Column(col) && isNumeric(value)) {
    return `${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} tCO₂e`
  }
  if (isNumeric(value) && !String(value).includes('-')) {
    return Number(value).toLocaleString('en-IN')
  }
  return String(value)
}

function toCSV(rows) {
  if (!rows?.length) return ''
  const headers = Object.keys(rows[0])
  const lines = [
    headers.join(','),
    ...rows.map(row =>
      headers.map(h => {
        const val = row[h] ?? ''
        return typeof val === 'string' && val.includes(',') ? `"${val}"` : val
      }).join(',')
    ),
  ]
  return lines.join('\n')
}

function downloadCSV(rows, filename = 'emissions_data.csv') {
  const csv = toCSV(rows)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ── Sub-components ────────────────────────────────────────────────────────────

function UserBubble({ text }) {
  return (
    <div className="flex justify-end mb-3">
      <div
        className="max-w-[80%] bg-emerald-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed shadow-sm"
        aria-label="Your message"
      >
        {text}
      </div>
    </div>
  )
}

function AssistantIcon() {
  return (
    <div className="flex-shrink-0 h-7 w-7 rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-white text-xs font-bold shadow-sm">
      🌿
    </div>
  )
}

function AssistantTextBubble({ text, execTimeMs }) {
  return (
    <div className="flex items-start gap-2 mb-3">
      <AssistantIcon />
      <div className="flex-1 min-w-0">
        <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 leading-relaxed shadow-sm">
          {text}
        </div>
        {execTimeMs > 0 && (
          <p className="text-[10px] text-slate-400 mt-1 ml-1">
            {(execTimeMs / 1000).toFixed(1)}s
          </p>
        )}
      </div>
    </div>
  )
}

function AssistantTableBubble({ rows, execTimeMs }) {
  const [expanded, setExpanded] = useState(false)
  if (!rows?.length) return null

  const headers     = Object.keys(rows[0])
  const visibleRows = expanded ? rows : rows.slice(0, 8)
  const hiddenCount = rows.length - 8

  return (
    <div className="flex items-start gap-2 mb-3">
      <AssistantIcon />
      <div className="flex-1 min-w-0">
        <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm shadow-sm overflow-hidden">
          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100 sticky top-0">
                  {headers.map(h => (
                    <th
                      key={h}
                      className={`px-3 py-2 font-semibold text-slate-600 whitespace-nowrap ${
                        isNumeric(rows[0][h]) ? 'text-right' : 'text-left'
                      }`}
                    >
                      {h.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, ri) => (
                  <tr key={ri} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    {headers.map(h => (
                      <td
                        key={h}
                        className={`px-3 py-2 text-slate-700 whitespace-nowrap ${
                          isNumeric(row[h]) ? 'text-right font-mono' : 'text-left'
                        } ${isCO2Column(h) ? 'text-teal-700 font-semibold' : ''}`}
                      >
                        {formatValue(h, row[h])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer actions */}
          <div className="px-3 py-2 border-t border-slate-100 flex items-center justify-between gap-2 bg-slate-50/50">
            <div className="flex items-center gap-2">
              {!expanded && hiddenCount > 0 && (
                <button
                  onClick={() => setExpanded(true)}
                  className="text-[11px] text-emerald-600 hover:text-emerald-700 font-medium hover:underline"
                >
                  Show all {rows.length} rows
                </button>
              )}
              {expanded && (
                <button
                  onClick={() => setExpanded(false)}
                  className="text-[11px] text-slate-400 hover:text-slate-600 font-medium hover:underline"
                >
                  Collapse
                </button>
              )}
            </div>
            <button
              onClick={() => downloadCSV(rows)}
              className="text-[11px] text-slate-400 hover:text-slate-600 flex items-center gap-1"
              title="Download as CSV"
            >
              ↓ CSV
            </button>
          </div>
        </div>
        {execTimeMs > 0 && (
          <p className="text-[10px] text-slate-400 mt-1 ml-1">
            {rows.length} rows · {(execTimeMs / 1000).toFixed(1)}s
          </p>
        )}
      </div>
    </div>
  )
}

function CustomChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-2 text-xs">
      {label && <p className="font-semibold text-slate-600 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <div key={i} className="flex justify-between gap-3">
          <span style={{ color: p.color }} className="font-medium">{p.name || p.dataKey}</span>
          <span className="text-slate-700 font-mono">
            {isNumeric(p.value) ? Number(p.value).toFixed(2) : p.value}
          </span>
        </div>
      ))}
    </div>
  )
}

function AssistantChartBubble({ chartConfig, chartData, execTimeMs }) {
  if (!chartConfig || !chartData?.length) return null

  const { type, title, x_key, y_key, color_key, y_label, x_label } = chartConfig

  const renderChart = () => {
    if (type === 'line') {
      const seriesKeys = color_key
        ? [...new Set(chartData.map(d => d[color_key]))]
        : [y_key]

      const pivotData = color_key
        ? Object.values(
            chartData.reduce((acc, row) => {
              const x = row[x_key]
              if (!acc[x]) acc[x] = { [x_key]: x }
              acc[x][row[color_key]] = row[y_key]
              return acc
            }, {})
          )
        : chartData

      return (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={pivotData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis dataKey={x_key} tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} width={45}
              tickFormatter={v => `${v}${y_label ? ' ' + y_label : ''}`} />
            <Tooltip content={<CustomChartTooltip />} />
            <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11 }} />
            {seriesKeys.map((key, i) => (
              <Line key={key} type="monotone" dataKey={color_key ? key : y_key}
                name={color_key ? key : (y_label || y_key)}
                stroke={CHART_COLORS[i % CHART_COLORS.length]}
                strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )
    }

    if (type === 'bar') {
      return (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis dataKey={x_key} tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} width={45}
              tickFormatter={v => `${v}`} />
            <Tooltip content={<CustomChartTooltip />} />
            <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey={y_key} name={y_label || y_key} radius={[4, 4, 0, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )
    }

    if (type === 'donut') {
      return (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey={y_key}
              nameKey={x_key}
              cx="50%" cy="50%"
              innerRadius={50} outerRadius={80}
              paddingAngle={2}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomChartTooltip />} />
            <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>
      )
    }

    return null
  }

  return (
    <div className="flex items-start gap-2 mb-3">
      <AssistantIcon />
      <div className="flex-1 min-w-0">
        <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm shadow-sm p-3">
          {title && (
            <p className="text-xs font-semibold text-slate-600 mb-2">{title}</p>
          )}
          {renderChart()}
          <div className="mt-2 flex justify-end">
            <button
              onClick={() => downloadCSV(chartData, `${title || 'chart'}.csv`)}
              className="text-[11px] text-slate-400 hover:text-slate-600"
            >
              ↓ Download CSV
            </button>
          </div>
        </div>
        {execTimeMs > 0 && (
          <p className="text-[10px] text-slate-400 mt-1 ml-1">
            {chartData.length} data points · {(execTimeMs / 1000).toFixed(1)}s
          </p>
        )}
      </div>
    </div>
  )
}

function LoadingBubble() {
  return (
    <div className="flex items-start gap-2 mb-3" aria-label="Assistant is thinking">
      <AssistantIcon />
      <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map(i => (
            <div
              key={i}
              className="h-2 w-2 rounded-full bg-emerald-400"
              style={{
                animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function ErrorBubble({ message, onRetry }) {
  return (
    <div className="flex items-start gap-2 mb-3">
      <AssistantIcon />
      <div className="flex-1">
        <div className="bg-red-50 border border-red-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-red-700 shadow-sm">
          <p className="font-medium mb-1">⚠ Couldn't answer that</p>
          <p className="text-red-600">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-1.5 ml-1 text-[11px] text-emerald-600 hover:text-emerald-700 font-medium hover:underline"
          >
            Try asking differently →
          </button>
        )}
      </div>
    </div>
  )
}

function StarterChips({ onSelect }) {
  return (
    <div className="px-4 py-5 flex flex-col items-center text-center">
      <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-2xl mb-3 shadow-lg">
        🌿
      </div>
      <h3 className="text-sm font-bold text-slate-800 mb-1">Emissions Assistant</h3>
      <p className="text-xs text-slate-500 mb-4">Ask anything about your carbon data</p>
      <div className="flex flex-wrap gap-2 justify-center">
        {STARTER_QUESTIONS.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            className="px-3 py-1.5 rounded-full bg-slate-100 hover:bg-emerald-50 hover:border-emerald-300 border border-slate-200 text-xs text-slate-600 hover:text-emerald-700 transition-all text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

function FollowUpChips({ questions, onSelect, visible }) {
  if (!visible || !questions?.length) return null
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pb-2">
      {questions.map((q, i) => (
        <button
          key={i}
          onClick={() => onSelect(q)}
          className="px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-xs text-emerald-700 hover:bg-emerald-100 transition-colors"
        >
          {q}
        </button>
      ))}
    </div>
  )
}

// ── Main Chat Panel ───────────────────────────────────────────────────────────

function ChatPanel({ isOpen, onClose }) {
  const [messages,        setMessages]        = useState([])
  const [input,           setInput]           = useState('')
  const [isLoading,       setIsLoading]       = useState(false)
  const [followUps,       setFollowUps]       = useState([])
  const [showFollowUps,   setShowFollowUps]   = useState(false)
  const [conversationId]                      = useState(getConversationId)
  const [pendingContext,  setPendingContext]   = useState(null)

  const messagesEndRef = useRef(null)
  const inputRef       = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages, isLoading])

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isOpen])

  // Expose openWithContext on window so review table can trigger without imports
  useEffect(() => {
    window.__chatbot = {
      openWithContext: (rowId, source) => {
        setPendingContext({ rowId, source })
        const msg = `Explain this ${source} row: ${rowId}`
        setInput(msg)
      },
    }
    return () => { delete window.__chatbot }
  }, [])

  const sendMessage = useCallback(async (text, ctx = null) => {
    const trimmed = (text || input).trim()
    if (!trimmed || isLoading) return

    const userMsg = { id: Date.now(), role: 'user', text: trimmed }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)
    setShowFollowUps(false)
    setFollowUps([])

    const context = ctx || pendingContext
    setPendingContext(null)

    try {
      const payload = {
        message:         trimmed,
        conversation_id: conversationId,
      }
      if (context?.rowId)  payload.context_row_id     = context.rowId
      if (context?.source) payload.context_row_source = context.source

      const { data } = await client.post('/chatbot/query/', payload)

      const assistantMsg = {
        id:           data.message_id || Date.now() + 1,
        role:         'assistant',
        type:         data.response_type || 'text',
        text:         data.answer,
        tableData:    data.table_data,
        chartConfig:  data.chart_config,
        chartData:    data.chart_data,
        execTimeMs:   data.execution_time_ms || 0,
        followUps:    data.suggested_follow_ups || [],
        error:        null,
      }

      setMessages(prev => [...prev, assistantMsg])
      setFollowUps(data.suggested_follow_ups || [])
      setShowFollowUps(true)

    } catch (err) {
      const errorText =
        err.response?.status === 429
          ? err.response?.data?.error || 'Rate limit reached. Please wait before asking again.'
          : err.response?.data?.error || 'Something went wrong. Please try again.'

      setMessages(prev => [
        ...prev,
        { id: Date.now() + 1, role: 'assistant', type: 'error', text: errorText },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, conversationId, pendingContext])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleInputChange = (e) => {
    setInput(e.target.value)
    if (e.target.value) setShowFollowUps(false)
  }

  const renderMessage = (msg) => {
    if (msg.role === 'user') {
      return <UserBubble key={msg.id} text={msg.text} />
    }

    if (msg.type === 'error') {
      return (
        <ErrorBubble
          key={msg.id}
          message={msg.text}
          onRetry={() => setInput(messages.find(m => m.role === 'user')?.text || '')}
        />
      )
    }

    if (msg.type === 'chart' && msg.chartConfig && msg.chartData?.length) {
      return (
        <div key={msg.id}>
          {msg.text && <AssistantTextBubble text={msg.text} execTimeMs={0} />}
          <AssistantChartBubble
            chartConfig={msg.chartConfig}
            chartData={msg.chartData}
            execTimeMs={msg.execTimeMs}
          />
        </div>
      )
    }

    if (msg.type === 'table' && msg.tableData?.length) {
      return (
        <div key={msg.id}>
          {msg.text && <AssistantTextBubble text={msg.text} execTimeMs={0} />}
          <AssistantTableBubble rows={msg.tableData} execTimeMs={msg.execTimeMs} />
        </div>
      )
    }

    return (
      <AssistantTextBubble key={msg.id} text={msg.text} execTimeMs={msg.execTimeMs} />
    )
  }

  const isEmpty = messages.length === 0 && !isLoading

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px]"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Panel */}
      <div
        role="dialog"
        aria-label="Emissions Assistant"
        aria-modal="true"
        className={`fixed right-0 top-0 h-full z-50 flex flex-col bg-white shadow-2xl border-l border-slate-200
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
          w-full sm:w-[420px] md:w-[480px]`}
      >
        {/* Header */}
        <div className="flex-shrink-0 px-4 py-4 border-b border-slate-100 bg-gradient-to-r from-emerald-50 to-teal-50/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-base shadow">
                🌿
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Emissions Assistant</h2>
                <p className="text-[11px] text-slate-500">Ask anything about your emissions data</p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close chat panel"
              className="h-8 w-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-white/80 transition-colors text-base"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 py-4 scroll-smooth">
          {isEmpty
            ? <StarterChips onSelect={(q) => sendMessage(q)} />
            : messages.map(renderMessage)
          }
          {isLoading && <LoadingBubble />}
          <div ref={messagesEndRef} />
        </div>

        {/* Follow-up chips */}
        <FollowUpChips
          questions={followUps}
          onSelect={(q) => sendMessage(q)}
          visible={showFollowUps && !isLoading}
        />

        {/* Input bar */}
        <div className="flex-shrink-0 border-t border-slate-100 bg-white px-3 py-3">
          <div className="flex items-end gap-2 bg-slate-50 rounded-2xl border border-slate-200 focus-within:border-emerald-300 focus-within:ring-2 focus-within:ring-emerald-100 transition-all px-3 py-2">
            <textarea
              ref={inputRef}
              id="chatbot-input"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type a question about your emissions data…"
              rows={1}
              disabled={isLoading}
              aria-label="Chat input"
              className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-400 resize-none outline-none leading-relaxed max-h-32 disabled:opacity-50"
              style={{ fieldSizing: 'content' }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
              className="flex-shrink-0 h-8 w-8 rounded-xl bg-emerald-600 flex items-center justify-center text-white text-sm font-bold disabled:opacity-40 hover:bg-emerald-700 transition-colors shadow-sm"
            >
              →
            </button>
          </div>
          <p className="text-[10px] text-slate-400 text-center mt-1.5">
            AI-generated · always verify before reporting
          </p>
        </div>
      </div>

      {/* Pulse animation keyframes (inline style tag) */}
      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </>
  )
}

// ── Floating Trigger Button ───────────────────────────────────────────────────

function FloatingButton({ isOpen, onClick, hasUnread }) {
  return (
    <button
      onClick={onClick}
      aria-label="Ask about your emissions data"
      title="Ask about your emissions data"
      className={`fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full
        bg-gradient-to-br from-emerald-500 to-teal-600
        text-white text-2xl shadow-xl hover:shadow-emerald-300/50
        hover:scale-105 active:scale-95 transition-all duration-200
        flex items-center justify-center
        ${isOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
    >
      🌿
      {hasUnread && (
        <span className="absolute top-1 right-1 h-3 w-3 rounded-full bg-amber-400 border-2 border-white animate-pulse" />
      )}
    </button>
  )
}

// ── Widget (default export) ───────────────────────────────────────────────────

export default function ChatbotWidget() {
  const [isOpen,    setIsOpen]    = useState(false)
  const [hasUnread, setHasUnread] = useState(false)

  const open  = () => { setIsOpen(true);  setHasUnread(false) }
  const close = () => setIsOpen(false)

  // Listen for external openWithContext calls
  useEffect(() => {
    const handler = () => { open() }
    window.addEventListener('chatbot:open', handler)
    return () => window.removeEventListener('chatbot:open', handler)
  }, [])

  return (
    <>
      <FloatingButton isOpen={isOpen} onClick={open} hasUnread={hasUnread} />
      <ChatPanel isOpen={isOpen} onClose={close} />
    </>
  )
}

// ── Named exports for external integration ───────────────────────────────────

/**
 * Call this from any component to open the chatbot pre-filled with
 * a row explanation request — without importing the whole widget.
 *
 * Usage (from review table row):
 *   import { openChatbotWithContext } from '../components/Chatbot'
 *   openChatbotWithContext('abc-123', 'UTILITY')
 */
export function openChatbotWithContext(rowId, source) {
  if (window.__chatbot?.openWithContext) {
    window.__chatbot.openWithContext(rowId, source)
  }
  window.dispatchEvent(new CustomEvent('chatbot:open'))
}
