/**
 * src/components/Charts/EmissionsByPlantChart.jsx
 * Horizontal bar chart — top facilities by CO₂e emissions
 */
import { useState, useEffect } from 'react'
import { getByPlant } from '../../api/charts'
import { formatCO2e } from '../../utils/chartFormatters'
import { ChartSkeleton, ChartEmpty, ChartCard } from './ChartSkeleton'
import TimeRangeSelector from './TimeRangeSelector'
import { useDashboardStore } from '../../store/dashboardStore'

// ISO 3166-1 alpha-2 → flag emoji
function countryFlag(code) {
  if (!code || code.length !== 2) return '🏭'
  return code
    .toUpperCase()
    .split('')
    .map(c => String.fromCodePoint(0x1F1E6 + c.charCodeAt(0) - 65))
    .join('')
}

export default function EmissionsByPlantChart() {
  const { byPlant: data, loadingPlant: loading, globalRange: range } = useDashboardStore()
  const [top, setTop]         = useState(10)
  
  // Note: the original allowed toggling top N locally. 
  // We can just slice the top N from the Zustand store which fetches top 10 by default!
  const displayData = data.slice(0, top)

  const maxVal = displayData.length > 0 ? Math.max(...displayData.map(d => d.co2e_kg)) : 1

  return (
    <ChartCard
      title="Top Facilities by Emissions"
      controls={
        <div className="flex items-center gap-2">
          {/* Top N selector */}
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
            {[5, 10].map(n => (
              <button
                key={n}
                onClick={() => setTop(n)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150
                  ${top === n ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200'}`}
              >
                Top {n}
              </button>
            ))}
          </div>
          <TimeRangeSelector
            value={range}
            onChange={(newRange) => useDashboardStore.getState().setGlobalRange(newRange)}
            options={['6m', '1y', 'all']}
          />
        </div>
      }
    >
      {loading ? (
        <ChartSkeleton height={280} />
      ) : data.length === 0 ? (
        <ChartEmpty />
      ) : (
        <div className="space-y-3 mt-1">
          {displayData.map((plant, idx) => {
            const barPct = maxVal > 0 ? (plant.co2e_kg / maxVal) * 100 : 0
            const isUnresolved = !plant.resolved || !plant.plant_name
            return (
              <div key={plant.plant_code} className="group">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs font-semibold text-slate-400 w-5 text-right flex-shrink-0">
                      {idx + 1}
                    </span>
                    <span className="text-base leading-none flex-shrink-0">
                      {countryFlag(plant.country)}
                    </span>
                    {isUnresolved ? (
                      <span className="text-xs font-medium text-amber-600 flex items-center gap-1 truncate">
                        <span>⚠️</span>
                        <span>WERKS {plant.plant_code}</span>
                        <span className="text-amber-400 font-normal">(unresolved)</span>
                      </span>
                    ) : (
                      <div className="min-w-0">
                        <span className="text-xs font-semibold text-slate-700 truncate block">
                          {plant.plant_name}
                        </span>
                        {plant.city && (
                          <span className="text-xs text-slate-400">{plant.city}</span>
                        )}
                      </div>
                    )}
                  </div>
                  <span className="text-xs font-semibold text-slate-600 ml-2 flex-shrink-0 whitespace-nowrap">
                    {formatCO2e(plant.co2e_kg)}{' '}
                    <span className="text-slate-400 font-normal">({plant.percentage}%)</span>
                  </span>
                </div>
                {/* Progress bar */}
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden ml-7">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${barPct}%`,
                      background: `linear-gradient(90deg, #10B981 0%, #059669 100%)`,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </ChartCard>
  )
}
