/**
 * HowItWorks.jsx — 3-step pipeline explanation (Light Theme)
 */
export default function HowItWorks() {
  const steps = [
    {
      num: '01',
      title: 'Ingest & Parse',
      desc: 'Upload raw SAP exports or Utility portals CSVs. Our Celery backend asynchronously parses varying formats into standardized staging rows.',
      color: 'blue',
    },
    {
      num: '02',
      title: 'Normalize & Review',
      desc: 'Plant codes map to global coordinates. Units (L, kg, m³) convert to standard metrics. ESG Analysts review and flag anomalies.',
      color: 'cyan',
    },
    {
      num: '03',
      title: 'Calculate & Lock',
      desc: 'Rows are multiplied by locked, date-valid emission factors (DEFRA, IPCC). Auditors lock the rows, making them immutable for reporting.',
      color: 'emerald',
    },
  ]

  const colorMap = {
    blue: 'text-blue-600 bg-blue-50 border-blue-200',
    cyan: 'text-cyan-600 bg-cyan-50 border-cyan-200',
    emerald: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  }

  return (
    <section id="how-it-works" className="py-24 px-6 bg-white relative">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-20">
          <h2 className="text-3xl sm:text-4xl font-black text-slate-900 mb-4 tracking-tight">
            How data flows into reports
          </h2>
          <p className="text-lg text-slate-600 max-w-xl mx-auto font-medium">
            From fragmented raw CSVs to an immutable, external-assurance-ready ledger.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 md:gap-8 relative">
          {/* Connecting line for desktop */}
          <div className="hidden md:block absolute top-8 left-[16%] right-[16%] h-0.5 bg-slate-200" />

          {steps.map((step, idx) => (
            <div key={step.num} className="relative z-10 flex flex-col items-center text-center">
              <div className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-black mb-6 shadow-sm border-2 ${colorMap[step.color]} bg-white`}>
                {step.num}
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">{step.title}</h3>
              <p className="text-sm text-slate-600 leading-relaxed font-medium">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
