/**
 * src/components/Charts/EmissionsBySourceChart.jsx
 * Stacked bar chart — monthly CO₂e by activity type
 */
import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { getBySource } from '../../api/charts'
import { formatMonth, formatCO2e, SOURCE_COLORS } from '../../utils/chartFormatters'
import { ChartSkeleton, ChartEmpty, ChartCard } from './ChartSkeleton'
import TimeRangeSelector from './TimeRangeSelector'
import { useDashboardStore } from '../../store/dashboardStore'

const BARS = [
  { key: 'fuel',             label: 'Fuel',             color: SOURCE_COLORS.fuel },
  { key: 'electricity',      label: 'Electricity',      color: SOURCE_COLORS.electricity },
  { key: 'flights',          label: 'Flights',          color: SOURCE_COLORS.flights },
  { key: 'hotels',           label: 'Hotels',           color: SOURCE_COLORS.hotels },
  { key: 'ground_transport', label: 'Ground Transport', color: SOURCE_COLORS.ground_transport },
]

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const total = payload.reduce((s, p) => s + (p.value || 0), 0)
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 min-w-[180px]">
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

export default function EmissionsBySourceChart() {
  const { bySource: data, loadingSource: loading, globalRange: range } = useDashboardStore()

  // kg → tonnes
  const chartData = data.map(d => ({
    ...d,
    fuel:             +(d.fuel             / 1000).toFixed(3),
    electricity:      +(d.electricity      / 1000).toFixed(3),
    flights:          +(d.flights          / 1000).toFixed(3),
    hotels:           +(d.hotels           / 1000).toFixed(3),
    ground_transport: +(d.ground_transport / 1000).toFixed(3),
  }))

  return (
    <ChartCard
      title="Emissions by Activity"
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
          <BarChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
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
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F8FAFC' }} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
            />
            {BARS.map(({ key, label, color }) => (
              <Bar key={key} dataKey={key} name={label} stackId="a" fill={color} radius={key === 'ground_transport' ? [3, 3, 0, 0] : [0, 0, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}
