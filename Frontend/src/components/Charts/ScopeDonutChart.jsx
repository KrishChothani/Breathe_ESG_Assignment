/**
 * src/components/Charts/ScopeDonutChart.jsx
 * Donut chart — Scope 1 / 2 / 3 breakdown
 */
import { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { getScopeBreakdown } from '../../api/charts'
import { formatCO2e, SCOPE_COLORS } from '../../utils/chartFormatters'
import { ChartSkeleton, ChartEmpty, ChartCard } from './ChartSkeleton'
import TimeRangeSelector from './TimeRangeSelector'
import { useDashboardStore } from '../../store/dashboardStore'

const SCOPES = [
  { key: 'scope_1', label: 'Scope 1', sub: 'Direct',      color: SCOPE_COLORS.scope_1 },
  { key: 'scope_2', label: 'Scope 2', sub: 'Electricity', color: SCOPE_COLORS.scope_2 },
  { key: 'scope_3', label: 'Scope 3', sub: 'Travel',      color: SCOPE_COLORS.scope_3 },
]

function CenterLabel({ viewBox, total }) {
  if (!viewBox || viewBox.cx === undefined || viewBox.cy === undefined) return null;
  const { cx, cy } = viewBox
  return (
    <g>
      <text x={cx} y={cy - 6} textAnchor="middle" dominantBaseline="middle"
        style={{ fontSize: 22, fontWeight: 700, fill: '#1E293B' }}>
        {(total / 1000).toFixed(1)}
      </text>
      <text x={cx} y={cy + 16} textAnchor="middle" dominantBaseline="middle"
        style={{ fontSize: 10, fill: '#94A3B8', fontWeight: 500 }}>
        tCO₂e Total
      </text>
    </g>
  )
}

export default function ScopeDonutChart() {
  const { scopeBreakdown: data, loadingScope: loading, globalRange: range } = useDashboardStore()
  const [active, setActive]   = useState(null)

  const pieData = data
    ? SCOPES.map(s => ({ name: s.label, value: data[s.key] || 0, ...s })).filter(d => d.value > 0)
    : []

  const total = data?.total || 0

  return (
    <ChartCard
      title="Emissions by Scope"
      controls={
        <TimeRangeSelector
          value={range}
          onChange={(newRange) => useDashboardStore.getState().setGlobalRange(newRange)}
          options={['30d', '6m', '1y', 'all']}
        />
      }
    >
      {loading ? (
        <ChartSkeleton height={240} />
      ) : !data || total === 0 ? (
        <ChartEmpty />
      ) : (
        <div className="flex flex-col items-center gap-4">
          {/* Donut */}
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={64}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
                onMouseEnter={(_, idx) => setActive(idx)}
                onMouseLeave={() => setActive(null)}
              >
                {pieData.map((entry, idx) => (
                  <Cell
                    key={entry.key}
                    fill={entry.color}
                    opacity={active === null || active === idx ? 1 : 0.45}
                    stroke="none"
                  />
                ))}
                <CenterLabel total={total} />
              </Pie>
              <Tooltip
                formatter={(val) => [formatCO2e(val), '']}
                contentStyle={{ borderRadius: 10, border: '1px solid #E5E7EB', fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div className="w-full space-y-2">
            {SCOPES.map(({ key, label, sub, color }) => {
              const val = data[key] || 0
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0
              return (
                <div key={key} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                    <span className="font-medium text-slate-700">{label}</span>
                    <span className="text-slate-400">— {sub}</span>
                  </div>
                  <div className="flex items-center gap-2 font-semibold">
                    <span className="text-slate-700">{formatCO2e(val)}</span>
                    <span className="text-slate-400 font-normal w-10 text-right">{pct}%</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </ChartCard>
  )
}
