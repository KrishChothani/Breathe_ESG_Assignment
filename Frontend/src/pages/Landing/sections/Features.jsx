/**
 * Features.jsx — 6-card feature grid (Alternating Dark Theme)
 */
const features = [
  {
    icon: '🏢',
    title: 'Scope 1 & 2 Normalisation',
    desc: 'Map SAP WERKS plant codes and utility meters to standard locations. Auto-convert litres, kg, and m³ to metric tonnes of CO₂e.',
  },
  {
    icon: '✈️',
    title: 'Scope 3 Travel Automation',
    desc: 'Connect corporate travel APIs. Automatically calculate aviation emissions with ICAO multipliers and hotel stays by region.',
  },
  {
    icon: '🔒',
    title: 'Immutable Audit Log',
    desc: 'Every approval, rejection, and value edit is permanently logged. Auditors can trace the exact factor used on the day of calculation.',
  },
  {
    icon: '🔮',
    title: 'Predictive Forecasting',
    desc: 'Use Holt-Winters exponential smoothing to predict your end-of-year emissions trajectory based on historical monthly run-rates.',
  },
  {
    icon: '📚',
    title: 'Factor Versioning',
    desc: 'Maintain DEFRA, IPCC, and CEA factors with validity dates. Ensure historical reports do not change when factors are updated.',
  },
  {
    icon: '📈',
    title: 'SEBI BRSR Intensity',
    desc: 'Calculate mandated metrics like Scope 1+2 emissions per rupee of turnover, automatically adjusted for PPP.',
  },
]

export default function Features() {
  return (
    <section id="features" className="py-24 px-6 bg-slate-900 relative">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />
      
      <div className="max-w-6xl mx-auto relative z-10">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-semibold mb-5 uppercase tracking-wide">
            Enterprise Grade
          </div>
          <h2 className="text-4xl sm:text-5xl font-black text-white mb-4 tracking-tight">
            Stop fighting with spreadsheets
          </h2>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto font-medium">
            A comprehensive suite of tools designed specifically for the rigorous
            requirements of external ESG assurance.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div
              key={f.title}
              className="p-8 rounded-2xl border border-slate-700 bg-slate-800 hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 transition-all group"
            >
              <div className="w-12 h-12 rounded-xl bg-slate-700 flex items-center justify-center text-2xl mb-6 group-hover:scale-110 transition-transform">
                {f.icon}
              </div>
              <h3 className="text-xl font-bold text-white mb-3">{f.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed font-medium">
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
