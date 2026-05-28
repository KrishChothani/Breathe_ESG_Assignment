/**
 * src/components/Forecast/ForecastSummaryTable.jsx
 *
 * YTD Actual | YTG Forecast | Full-FY Run Rate breakdown table.
 * Visual distinction: YTG rows have a dashed left border.
 */
import ConfidenceBadge from './ConfidenceBadge'
import ForecastMethodBadge from './ForecastMethodBadge'

function fmt(val, decimals = 1) {
  if (val == null) return '—'
  return `${Number(val).toFixed(decimals)}`
}

function ScopeLabel({ scope }) {
  const map = {
    scope_1: { label: 'Scope 1', sub: 'Direct (Fuel)',         dot: 'bg-orange-400' },
    scope_2: { label: 'Scope 2', sub: 'Purchased Electricity', dot: 'bg-blue-400'   },
    scope_3: { label: 'Scope 3', sub: 'Business Travel',       dot: 'bg-violet-400' },
  }
  const m = map[scope] ?? { label: scope, sub: '', dot: 'bg-slate-400' }
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full shrink-0 ${m.dot}`} />
      <div>
        <p className="text-xs font-bold text-slate-800">{m.label}</p>
        <p className="text-[10px] text-slate-400">{m.sub}</p>
      </div>
    </div>
  )
}

export default function ForecastSummaryTable({ ytdActuals, ytgForecast, annualizedRunRate, monthsElapsed, isPastFY }) {
  if (!ytdActuals) return null

  const scopes = ['scope_1', 'scope_2', 'scope_3']
  const methods = { scope_1: 'RUN_RATE', scope_2: 'ETS', scope_3: 'ACTIVITY_DRIVEN' }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-slate-100">
            <th className="text-left py-2 pr-3 text-slate-500 font-semibold text-[10px] uppercase tracking-wider w-28">Scope</th>
            <th className="text-right py-2 px-2 text-slate-500 font-semibold text-[10px] uppercase tracking-wider">
              {isPastFY ? 'Full-Year Actual' : 'YTD Actual'}<br/>
              <span className="normal-case font-normal text-slate-400">({monthsElapsed} mo.)</span>
            </th>
            {!isPastFY && (
              <>
                <th className="text-right py-2 px-2 text-slate-500 font-semibold text-[10px] uppercase tracking-wider">
                  YTG Forecast<br/>
                  <span className="normal-case font-normal text-slate-400">({12 - (monthsElapsed || 0)} mo.)</span>
                </th>
                <th className="text-right py-2 pl-2 text-slate-500 font-semibold text-[10px] uppercase tracking-wider">Full-FY Rate</th>
              </>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {scopes.map(sc => {
            const ytd  = ytdActuals?.[sc]
            const ytg  = ytgForecast?.[sc]
            const arr  = annualizedRunRate?.[sc]
            const ytgMethod = ytgForecast?.[sc]?.method || methods[sc]
            return (
              <tr key={sc} className="group hover:bg-slate-50/60 transition-colors">
                <td className="py-3 pr-3">
                  <ScopeLabel scope={sc} />
                </td>

                {/* YTD Actual */}
                <td className="py-3 px-2 text-right">
                  <p className="font-mono font-bold text-slate-800">
                    {fmt(ytd?.co2e_tonnes)} <span className="text-slate-400 font-normal">tCO₂e</span>
                  </p>
                </td>

                {/* YTG Forecast — only for current/future FY */}
                {!isPastFY && (
                  <>
                    <td className="py-3 px-2 text-right border-l-2 border-dashed border-slate-200">
                      <p className="font-mono font-bold text-slate-700">
                        {fmt(ytg?.co2e_tonnes)} <span className="text-slate-400 font-normal">tCO₂e</span>
                      </p>
                      {ytg?.lower != null && (
                        <p className="text-slate-400 text-[10px] font-mono">
                          {fmt(ytg.lower, 0)}–{fmt(ytg.upper, 0)} CI
                        </p>
                      )}
                      <div className="flex items-center justify-end gap-1 mt-1">
                        <ForecastMethodBadge method={ytgMethod} />
                        <ConfidenceBadge value={ytg?.confidence_pct} />
                      </div>
                    </td>
                    <td className="py-3 pl-2 text-right">
                      <p className="font-mono text-slate-500">
                        {fmt(arr)} <span className="text-slate-300 font-normal">t</span>
                      </p>
                    </td>
                  </>
                )}
              </tr>
            )
          })}
        </tbody>
        <tfoot className="border-t-2 border-slate-200">
          <tr className="bg-slate-50/50">
            <td className="py-2.5 pr-3 text-xs font-bold text-slate-700">TOTAL</td>
            <td className="py-2.5 px-2 text-right font-mono font-bold text-slate-800 text-xs">
              {fmt(ytdActuals?.total?.co2e_tonnes)} t
            </td>
            {!isPastFY && (
              <>
                <td className="py-2.5 px-2 text-right font-mono font-bold text-slate-700 text-xs border-l-2 border-dashed border-slate-200">
                  {fmt(ytgForecast?.total?.co2e_tonnes)} t
                  {ytgForecast?.total?.lower != null && (
                    <span className="text-slate-400 text-[10px] block">
                      {fmt(ytgForecast.total.lower, 0)}–{fmt(ytgForecast.total.upper, 0)} CI
                    </span>
                  )}
                </td>
                <td className="py-2.5 pl-2 text-right font-mono text-slate-500 text-xs">
                  {fmt(annualizedRunRate?.total)} t
                </td>
              </>
            )}
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
