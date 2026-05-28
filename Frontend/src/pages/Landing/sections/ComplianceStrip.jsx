/**
 * ComplianceStrip.jsx — Regulatory frameworks compliance badges (Dark Theme)
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
  emerald: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  blue:    'border-blue-500/30 bg-blue-500/10 text-blue-300',
  indigo:  'border-indigo-500/30 bg-indigo-500/10 text-indigo-300',
  violet:  'border-violet-500/30 bg-violet-500/10 text-violet-300',
  amber:   'border-amber-500/30 bg-amber-500/10 text-amber-300',
  rose:    'border-rose-500/30 bg-rose-500/10 text-rose-300',
  teal:    'border-teal-500/30 bg-teal-500/10 text-teal-300',
}

export default function ComplianceStrip() {
  return (
    <section id="compliance" className="py-24 px-6 relative bg-slate-900">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

      <div className="max-w-7xl mx-auto relative z-10">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-400 text-xs font-semibold mb-5 uppercase tracking-wide">
            Regulatory Compliance
          </div>
          <h2 className="text-4xl sm:text-5xl font-black text-white mb-4 tracking-tight">
            Built on the frameworks
            <br />
            <span className="text-blue-400">
              auditors actually use
            </span>
          </h2>
          <p className="text-lg text-slate-400 max-w-xl mx-auto font-medium">
            Every emission factor, every GWP value, every grid intensity is traceable
            to a published regulatory source.
          </p>
        </div>

        {/* Badge grid */}
        <div className="flex flex-wrap justify-center gap-3 mb-14">
          {frameworks.map((f) => (
            <div
              key={f.short}
              className={`flex flex-col items-center px-5 py-3.5 rounded-xl border ${colorMap[f.color]} transition-all hover:-translate-y-0.5`}
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
              className="p-6 rounded-2xl border border-slate-700 bg-slate-800 hover:border-blue-500/50 transition-all"
            >
              <span className="text-3xl mb-3 block">{d.icon}</span>
              <h3 className="text-sm font-bold text-white mb-2">{d.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed font-medium">{d.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
