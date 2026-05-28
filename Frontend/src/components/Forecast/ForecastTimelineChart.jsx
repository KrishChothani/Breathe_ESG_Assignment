/**
 * src/components/Forecast/ForecastTimelineChart.jsx
 *
 * 12-month ComposedChart showing:
 *   LEFT of "today" divider  → solid Area (actuals, dark slate)
 *   RIGHT of "today" divider → dashed Area (forecast, slate-400)
 *   Confidence band          → two transparent Area layers (lower/upper)
 *
 * Props:
 *   monthlyTimeline  — from API response monthly_timeline array
 *   monthsElapsed    — number of complete months with actuals
 */
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts'
import { useMemo } from 'react'

const MONTH_ABBR = ['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const isActual = payload[0]?.payload?.is_actual

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs min-w-[200px]">
      <p className="font-bold text-slate-700 mb-2 flex items-center gap-1.5">
        {label}
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${
          isActual
            ? 'bg-slate-100 text-slate-600'
            : 'bg-violet-50 text-violet-600 border border-violet-200'
        }`}>
          {isActual ? 'Actual' : 'Forecast'}
        </span>
      </p>
      {payload.map(p => {
        if (p.dataKey === 'confidence_band' || p.dataKey === 'ci_lower') return null
        if (p.value == null || p.value === undefined) return null
        return (
          <div key={p.dataKey} className="flex justify-between gap-4">
            <span className="text-slate-500">{p.name}</span>
            <span className="font-mono font-bold text-slate-800">
              {Number(p.value).toFixed(2)} tCO₂e
            </span>
          </div>
        )
      })}
      {!isActual && payload[0]?.payload?.ci_lower != null && (
        <p className="text-slate-400 mt-1.5 pt-1.5 border-t border-slate-100">
          CI: {Number(payload[0].payload.ci_lower).toFixed(1)} – {Number(payload[0].payload.ci_upper).toFixed(1)} tCO₂e
        </p>
      )}
    </div>
  )
}

export default function ForecastTimelineChart({ monthlyTimeline = [], monthsElapsed = 0 }) {
  const data = useMemo(() => {
    if (!monthlyTimeline?.length) return []

    return monthlyTimeline.map((row, idx) => {
      const label = MONTH_ABBR[idx] ?? row.month
      const total = Number(row.total || 0)
      const isActual = row.is_actual

      // Confidence interval total (sum of scope bounds)
      const ciLower = !isActual
        ? (Number(row.scope_1_lower || 0) + Number(row.scope_2_lower || 0) + Number(row.scope_3_lower || 0))
        : null
      const ciUpper = !isActual
        ? (Number(row.scope_1_upper || 0) + Number(row.scope_2_upper || 0) + Number(row.scope_3_upper || 0))
        : null

      return {
        label,
        month: row.month,
        month_number: row.month_number,
        is_actual: isActual,
        actual_total:   isActual ? total : null,
        forecast_total: !isActual ? total : null,
        ci_lower:  ciLower,
        ci_upper:  ciUpper,
        // For the confidence band area (upper - lower)
        confidence_band: ciLower != null && ciUpper != null ? [ciLower, ciUpper] : null,
      }
    })
  }, [monthlyTimeline])

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
        No forecast data available
      </div>
    )
  }

  // Divider label = last actual month label
  const dividerLabel = data[monthsElapsed - 1]?.label ?? ''

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#1e293b" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#1e293b" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#94a3b8" stopOpacity={0.20} />
            <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="ciGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#8b5cf6" stopOpacity={0.10} />
            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 10 }}
          tickFormatter={v => `${v.toFixed(0)}`}
          axisLine={false} tickLine={false} width={45}
          label={{ value: 'tCO₂e', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 9, fill: '#94a3b8' } }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={(value) => <span style={{ color: '#475569' }}>{value}</span>}
        />

        {/* Reference line: "Today" divider */}
        {monthsElapsed > 0 && monthsElapsed < 12 && (
          <ReferenceLine
            x={data[monthsElapsed - 1]?.label}
            stroke="#e2e8f0"
            strokeDasharray="4 2"
            strokeWidth={1.5}
            label={{ value: 'Today →', position: 'top', fontSize: 9, fill: '#94a3b8', offset: 4 }}
          />
        )}

        {/* CI band — upper boundary */}
        <Area
          dataKey="ci_upper"
          name="CI Upper"
          stroke="none"
          fill="url(#ciGrad)"
          fillOpacity={1}
          connectNulls
          legendType="none"
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />
        {/* CI band — lower boundary (renders on top of upper, creates band effect) */}
        <Area
          dataKey="ci_lower"
          name="90% CI"
          stroke="#8b5cf6"
          strokeWidth={0}
          strokeDasharray="3 3"
          fill="white"
          fillOpacity={1}
          connectNulls
          legendType="square"
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />

        {/* Actuals — solid */}
        <Area
          dataKey="actual_total"
          name="Actual"
          stroke="#1e293b"
          strokeWidth={2}
          fill="url(#actualGrad)"
          connectNulls={false}
          dot={{ r: 3, fill: '#1e293b', strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />

        {/* Forecast — dashed */}
        <Area
          dataKey="forecast_total"
          name="Forecast"
          stroke="#94a3b8"
          strokeWidth={2}
          strokeDasharray="6 3"
          fill="url(#forecastGrad)"
          connectNulls={false}
          dot={{ r: 3, fill: '#94a3b8', strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
