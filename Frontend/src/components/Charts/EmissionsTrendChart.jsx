/**
 * src/components/Charts/EmissionsTrendChart.jsx
 * Line chart — monthly CO₂e by source (SAP / Utility / Travel)
 */
import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Dot
} from 'recharts'
import { getTrendData } from '../../api/charts'
import { formatMonth, formatCO2e, SOURCE_COLORS } from '../../utils/chartFormatters'
import { ChartSkeleton, ChartEmpty, ChartCard } from './ChartSkeleton'
import TimeRangeSelector from './TimeRangeSelector'
import { useDashboardStore } from '../../store/dashboardStore'

const LINES = [
  { key: 'SAP',     label: 'SAP (Fuel)',   color: SOURCE_COLORS.SAP },
  { key: 'UTILITY', label: 'Utility',      color: SOURCE_COLORS.UTILITY },
  { key: 'TRAVEL',  label: 'Travel',       color: SOURCE_COLORS.TRAVEL },
]

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const total = payload.reduce((s, p) => s + (p.value || 0), 0)
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 min-w-[160px]">
      <p className="text-xs font-semibold text-slate-600 mb-2">{formatMonth(label)}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex justify-between gap-4 text-xs mb-1">
          <span style={{ color: p.color }} className="font-medium">{p.name}</span>
          <span className="text-slate-700 font-semibold">{formatCO2e(p.value * 1000)}</span>
        </div>
      ))}
      <div className="border-t border-gray-100 mt-2 pt-1 flex justify-between text-xs font-bold">
        <span className="text-slate-500">Total</span>
        <span className="text-slate-800">{formatCO2e(total * 1000)}</span>
      </div>
    </div>
  )
}

export default function EmissionsTrendChart() {
  const { trend: data, loadingTrend: loading, globalRange: range } = useDashboardStore()

  // Convert kg → tonnes for Y-axis readability
  const chartData = data.map(d => ({
    ...d,
    SAP:     +(d.SAP     / 1000).toFixed(2),
    UTILITY: +(d.UTILITY / 1000).toFixed(2),
    TRAVEL:  +(d.TRAVEL  / 1000).toFixed(2),
  }))

  const showDots = ['7d', '30d', '90d'].includes(range)

  return (
    <ChartCard
      title="Emissions Over Time"
      controls={
        <TimeRangeSelector
          value={range}
          onChange={(newRange) => useDashboardStore.getState().setGlobalRange(newRange)}
          options={['30d', '90d', '6m', '1y', 'all']}
        />
      }
    >
      {loading ? (
        <ChartSkeleton height={280} />
      ) : chartData.length === 0 ? (
        <ChartEmpty />
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis
              dataKey="month"
              tickFormatter={formatMonth}
              tick={{ fontSize: 11, fill: '#94A3B8' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#94A3B8' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => `${v}t`}
              width={40}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
            />
            {LINES.map(({ key, label, color }) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                name={label}
                stroke={color}
                strokeWidth={2.5}
                dot={showDots ? { r: 3, fill: color } : false}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}
