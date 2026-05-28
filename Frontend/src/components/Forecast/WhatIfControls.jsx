/**
 * src/components/Forecast/WhatIfControls.jsx
 *
 * Collapsible panel with three Scope 3 activity driver sliders.
 * Drivers affect only Scope 3 (Activity-Driven formula).
 * Changes are debounced 400ms in the Zustand store before triggering API re-fetch.
 */
import { useState } from 'react'
import { useForecastStore } from '../../store/forecastStore'

function DriverSlider({ id, label, description, value, onChange, disabled }) {
  const pct = Math.round(value * 100)
  const color = pct > 0 ? 'text-rose-600' : pct < 0 ? 'text-emerald-600' : 'text-slate-500'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-xs font-semibold text-slate-700">{label}</label>
        <span className={`text-xs font-mono font-bold ${color}`}>
          {pct > 0 ? '+' : ''}{pct}%
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={-50}
        max={50}
        step={5}
        value={pct}
        disabled={disabled}
        onChange={e => onChange(Number(e.target.value) / 100)}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer
                   bg-slate-200 accent-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
      />
      <p className="text-[10px] text-slate-400">{description}</p>
    </div>
  )
}

export default function WhatIfControls({ loading }) {
  const [open, setOpen] = useState(false)
  const { activityDrivers, setActivityDriver, resetDrivers } = useForecastStore()

  const hasChanges = Object.values(activityDrivers).some(v => v !== 0)

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3
                   bg-slate-50 hover:bg-slate-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-700">🎛️ What-If Scenario Analysis</span>
          {hasChanges && (
            <span className="text-[10px] font-bold bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full">
              Modified
            </span>
          )}
        </div>
        <span className="text-slate-400 text-xs font-medium">
          {open ? '▲ Hide' : '▼ Show'}
        </span>
      </button>

      {open && (
        <div className="p-4 space-y-5">
          {/* Info banner */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5 text-[11px] text-amber-700">
            <strong>Scope 3 only:</strong> These sliders apply the Activity-Driven formula
            (E<sub>projected</sub> = H<sub>j</sub> × (1 + ΔD)) to remaining travel months.
            Scope 1 (Run Rate) and Scope 2 (ETS) are data-driven and unaffected.
          </div>

          {/* Sliders */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <DriverSlider
              id="driver-air"
              label="✈️ Air Travel Volume"
              description="±% vs. prior-FY same-month baseline for remaining months"
              value={activityDrivers.air_travel}
              onChange={v => setActivityDriver('air_travel', v)}
              disabled={loading}
            />
            <DriverSlider
              id="driver-hotel"
              label="🏨 Hotel Night Volume"
              description="±% change in hotel nights booked"
              value={activityDrivers.hotel_stays}
              onChange={v => setActivityDriver('hotel_stays', v)}
              disabled={loading}
            />
            <DriverSlider
              id="driver-ground"
              label="🚗 Ground Transport"
              description="±% change in car/rail/taxi usage"
              value={activityDrivers.ground_transport}
              onChange={v => setActivityDriver('ground_transport', v)}
              disabled={loading}
            />
          </div>

          {/* Reset button */}
          {hasChanges && (
            <div className="flex justify-end">
              <button
                onClick={resetDrivers}
                disabled={loading}
                className="text-xs text-slate-500 hover:text-slate-700 underline underline-offset-2
                           disabled:opacity-40 transition-colors"
              >
                Reset to baseline
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
