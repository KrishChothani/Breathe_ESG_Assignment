/**
 * src/components/Charts/ReviewPipelineChart.jsx
 * Custom progress-bar pipeline — shows current review status across all rows.
 * Clicking a status navigates to /review?status=<STATUS>
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChartCard } from './ChartSkeleton'
import { useDashboardStore } from '../../store/dashboardStore'

const STAGES = [
  { key: 'pending',  label: 'Pending',  color: '#94A3B8', bg: '#F1F5F9', text: '#64748B' },
  { key: 'flagged',  label: 'Flagged',  color: '#F59E0B', bg: '#FFFBEB', text: '#92400E' },
  { key: 'approved', label: 'Approved', color: '#22C55E', bg: '#F0FDF4', text: '#166534' },
  { key: 'rejected', label: 'Rejected', color: '#EF4444', bg: '#FEF2F2', text: '#991B1B' },
  { key: 'locked',   label: 'Locked',   color: '#3B82F6', bg: '#EFF6FF', text: '#1E40AF' },
]

function PipelineSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {STAGES.map(s => (
        <div key={s.key} className="space-y-1">
          <div className="flex justify-between">
            <div className="h-3 w-16 bg-slate-200 rounded" />
            <div className="h-3 w-10 bg-slate-200 rounded" />
          </div>
          <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full w-2/5 bg-slate-200 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ReviewPipelineChart() {
  const { reviewPipeline: data, loadingPipeline: loading } = useDashboardStore()
  const navigate              = useNavigate()

  const total = data?.total || 0

  return (
    <ChartCard title="Review Pipeline">
      {loading ? (
        <PipelineSkeleton />
      ) : !data || total === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 gap-2 text-center">
          <span className="text-3xl">✅</span>
          <p className="text-sm text-slate-400">No rows in the review pipeline yet.</p>
        </div>
      ) : (
        <div className="space-y-1">
          {STAGES.map(({ key, label, color, bg, text }) => {
            const count = data[key] ?? 0
            const pct   = total > 0 ? (count / total) * 100 : 0
            return (
              <button
                key={key}
                onClick={() => navigate(`/review?status=${key.toUpperCase()}`)}
                className="w-full text-left group hover:opacity-90 transition-opacity"
                title={`Go to ${label} reviews`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs font-semibold" style={{ color: text }}>
                      {label}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 font-medium">
                    {count.toLocaleString()} rows
                  </span>
                </div>
                <div
                  className="h-2.5 rounded-full overflow-hidden mb-3"
                  style={{ backgroundColor: bg }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
              </button>
            )
          })}

          {/* Approval rate footer */}
          <div className="border-t border-gray-100 pt-3 mt-1">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500 font-medium">Approval rate</span>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all duration-700"
                    style={{ width: `${data.approval_rate ?? 0}%` }}
                  />
                </div>
                <span className="text-sm font-bold text-emerald-700">
                  {data.approval_rate ?? 0}%
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {total.toLocaleString()} total rows across all sources
            </p>
          </div>
        </div>
      )}
    </ChartCard>
  )
}
