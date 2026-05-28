/**
 * ComplianceStrip.jsx — Regulatory frameworks compliance badges (Light Theme)
 */
const frameworks = [
  { short: 'SEBI BRSR', full: 'SEBI Circular 2023/122', color: 'emerald' },
  { short: 'GHG Protocol', full: 'Corporate Standard', color: 'blue' },
  { short: 'IPCC AR6', full: 'GWP100 Factors', color: 'indigo' },
  { short: 'DEFRA 2024', full: 'UK GHG Conv. Factors', color: 'violet' },
  { short: 'CEA V20', full: 'India Grid Emissions', color: 'amber' },
  { short: 'ICAO 2023', full: 'Aviation Emissions', color: 'rose' },
  { short: 'India GHG', full: 'Program Factors', color: 'teal' },
]

const colorMap = {
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  blue:    'border-blue-200 bg-blue-50 text-blue-800',
  indigo:  'border-indigo-200 bg-indigo-50 text-indigo-800',
  violet:  'border-violet-200 bg-violet-50 text-violet-800',
  amber:   'border-amber-200 bg-amber-50 text-amber-800',
  rose:    'border-rose-200 bg-rose-50 text-rose-800',
  teal:    'border-teal-200 bg-teal-50 text-teal-800',
}

export default function ComplianceStrip() {
  return (
    <section id="compliance" className="py-24 px-6 relative bg-white border-t border-slate-200">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-violet-200 bg-violet-50 text-violet-700 text-xs font-semibold mb-5 uppercase tracking-wide">
            Regulatory Compliance
          </div>
          <h2 className="text-4xl sm:text-5xl font-black text-slate-900 mb-4 tracking-tight">
            Built on the frameworks
            <br />
            <span className="text-blue-600">
              auditors actually use
            </span>
          </h2>
          <p className="text-lg text-slate-600 max-w-xl mx-auto font-medium">
            Every emission factor, every GWP value, every grid intensity is traceable
            to a published regulatory source.
          </p>
        </div>

        {/* Badge grid */}
        <div className="flex flex-wrap justify-center gap-3 mb-14">
          {frameworks.map((f) => (
            <div
              key={f.short}
              className={`flex flex-col items-center px-5 py-3.5 rounded-xl border-2 ${colorMap[f.color]} transition-all hover:-translate-y-0.5 shadow-sm`}
            >
              <span className="text-sm font-bold">{f.short}</span>
              <span className="text-[10px] opacity-80 mt-0.5 font-medium">{f.full}</span>
            </div>
          ))}
        </div>

        {/* Detail row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            {
              icon: '🔒',
              title: 'Emission Factor Immutability',
              desc: 'Historical calculations are frozen at the factor used at ingestion time. Updating a factor for FY 2025-26 never retroactively changes FY 2024-25 figures.',
            },
            {
              icon: '📐',
              title: 'Intensity Ratios',
              desc: 'Total Scope 1+2 CO₂e (MT) ÷ Revenue from Operations (PPP-adjusted USD) computed as mandated by SEBI BRSR Core.',
            },
            {
              icon: '✅',
              title: 'External Assurance Ready',
              desc: 'Every row carries a human-readable formula, factor source, factor version, and factor UUID. No black boxes for your Big 4 assurance partner.',
            },
          ].map((d) => (
            <div
              key={d.title}
              className="p-6 rounded-2xl border border-slate-200 bg-white hover:border-blue-300 hover:shadow-md transition-all"
            >
              <span className="text-3xl mb-3 block">{d.icon}</span>
              <h3 className="text-sm font-bold text-slate-900 mb-2">{d.title}</h3>
              <p className="text-xs text-slate-600 leading-relaxed font-medium">{d.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
