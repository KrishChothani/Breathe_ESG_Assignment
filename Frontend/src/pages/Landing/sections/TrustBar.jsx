/**
 * TrustBar.jsx — Logos / Data Sources strip (Light Theme)
 */
export default function TrustBar() {
  return (
    <section className="py-12 border-y border-slate-200 bg-white">
      <div className="max-w-7xl mx-auto px-6 text-center">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-8">
          Seamlessly ingest data from your enterprise tools
        </p>
        <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-16 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
          {/* Logos text representation since no actual SVGs */}
          {['SAP S/4HANA', 'Concur', 'Navan', 'Salesforce NetZero', 'Oracle Fusion'].map((brand) => (
            <span key={brand} className="text-lg font-black tracking-tight text-slate-800">
              {brand}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
