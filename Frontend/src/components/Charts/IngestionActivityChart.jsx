/**
 * src/components/Charts/IngestionActivityChart.jsx
 * Area chart — daily data ingestion activity (rows ingested vs failed)
 */
import { useState, useEffect } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { getIngestionActivity } from '../../api/charts'
import { formatDate } from '../../utils/chartFormatters'
import { ChartSkeleton, ChartEmpty, ChartCard } from './ChartSkeleton'
import TimeRangeSelector from './TimeRangeSelector'
import { useDashboardStore } from '../../store/dashboardStore'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const ingested = payload.find(p => p.dataKey === 'rows_ingested')?.value ?? 0
  const failed   = payload.find(p => p.dataKey === 'rows_failed')?.value ?? 0
  const uploads  = payload.find(p => p.dataKey === 'uploads')?.value ?? 0
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 min-w-[180px]">
      <p className="text-xs font-semibold text-slate-600 mb-2">{formatDate(label)}</p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-slate-500">Uploads</span>
          <span className="font-semibold text-slate-700">{uploads}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-emerald-600">Rows Ingested</span>
          <span className="font-semibold text-emerald-700">{ingested.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-rose-500">Rows Failed</span>
          <span className="font-semibold text-rose-600">{failed.toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

export default function IngestionActivityChart() {
  const { ingestionActivity: data, loadingActivity: loading, fetchIngestionActivity } = useDashboardStore()
  const [range, setRange]     = useState('30d')

  // Refetch only this chart when its local range changes
  useEffect(() => {
    // Avoid double fetching on mount if it's already 30d and loaded
    if (range === '30d' && data.length > 0) return
    fetchIngestionActivity(range)
  }, [range])

  return (
    <ChartCard
      title="Data Ingestion Activity"
      controls={
        <TimeRangeSelector
          value={range}
          onChange={setRange}
          options={['7d', '30d', '90d']}
        />
      }
    >
      {loading ? (
        <ChartSkeleton height={200} />
      ) : data.length === 0 ? (
        <ChartEmpty />
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="ingGreen" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#22C55E" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#22C55E" stopOpacity={0.03} />
              </linearGradient>
              <linearGradient id="ingRed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#EF4444" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#EF4444" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={d => {
                if (!d) return ''
                const parts = d.split('-')
                return `${parts[2]}/${parts[1]}`
              }}
              tick={{ fontSize: 10, fill: '#94A3B8' }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#94A3B8' }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            />
            <Area
              type="monotone"
              dataKey="rows_ingested"
              name="Rows Ingested"
              stroke="#22C55E"
              strokeWidth={2}
              fill="url(#ingGreen)"
              dot={false}
              activeDot={{ r: 4, fill: '#22C55E' }}
            />
            <Area
              type="monotone"
              dataKey="rows_failed"
              name="Rows Failed"
              stroke="#EF4444"
              strokeWidth={2}
              fill="url(#ingRed)"
              dot={false}
              activeDot={{ r: 4, fill: '#EF4444' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}
