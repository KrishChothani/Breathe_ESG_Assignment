/**
 * ProductPreview.jsx — Alternating dark theme 6-image product carousel
 */
import { useState, useEffect } from 'react'
import img1 from '../../../assets/image1.png'
import img2 from '../../../assets/image2.png'
import img3 from '../../../assets/image3.png'
import img4 from '../../../assets/image4.png'
import img5 from '../../../assets/image5.png'
import img6 from '../../../assets/image6.png'

const slides = [
  { id: 1, src: img1, title: 'Executive Dashboard', desc: 'Real-time Scope 1, 2, and 3 emissions tracking with year-on-year analysis.' },
  { id: 2, src: img2, title: 'Predictive Forecasting', desc: 'Holt-Winters ETS models projecting end-of-year emissions run-rate.' },
  { id: 3, src: img3, title: 'Analyst Review Queue', desc: 'Audit-ready pipeline showing raw utility bills and SAP rows pending approval.' },
  { id: 4, src: img4, title: 'Plant Registry Map', desc: 'Master data mapping SAP WERKS codes to physical global facilities.' },
  { id: 5, src: img5, title: 'BRSR Core Reports', desc: 'Auto-generated SEBI BRSR Core disclosures ready for external assurance.' },
  { id: 6, src: img6, title: 'Emission Factors Library', desc: 'Scientifically backed global factors (DEFRA, IPCC, CEA) locked via UUID.' },
]

export default function ProductPreview() {
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % slides.length)
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  return (
    <section className="py-24 px-6 relative bg-slate-900">
      <div className="absolute inset-0 bg-gradient-to-b from-slate-900 via-blue-900/10 to-slate-900 pointer-events-none" />

      <div className="max-w-6xl mx-auto relative z-10">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-semibold mb-5 uppercase tracking-wide">
            Live Platform
          </div>
          <h2 className="text-4xl sm:text-5xl font-black text-white mb-5 tracking-tight">
            A dashboard built for
            <br />
            <span className="text-blue-400">
              real ESG analysts
            </span>
          </h2>
          <p className="text-lg text-slate-400 max-w-xl mx-auto">
            Not a spreadsheet. Not a BI tool bolted onto compliance forms.
            A purpose-built enterprise carbon accounting platform.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-center">
          
          <div className="w-full lg:w-1/3 flex flex-col gap-3">
            {slides.map((slide, idx) => (
              <button
                key={slide.id}
                onClick={() => setCurrent(idx)}
                className={`text-left p-4 rounded-xl border-2 transition-all ${
                  current === idx
                    ? 'border-blue-500 bg-slate-800 shadow-md shadow-blue-500/10'
                    : 'border-transparent hover:bg-slate-800/50'
                }`}
              >
                <h3 className={`text-sm font-bold mb-1 ${current === idx ? 'text-blue-400' : 'text-slate-300'}`}>
                  {slide.title}
                </h3>
                <p className={`text-xs leading-relaxed ${current === idx ? 'text-blue-300' : 'text-slate-500'}`}>
                  {slide.desc}
                </p>
              </button>
            ))}
          </div>

          <div className="w-full lg:w-2/3">
            <div className="relative rounded-2xl overflow-hidden border border-slate-700 shadow-2xl shadow-black/50 bg-slate-800 group aspect-[16/10] sm:aspect-video flex items-center justify-center">
              
              <div className="absolute top-0 inset-x-0 flex items-center gap-3 px-4 py-3 bg-[#0d1117] border-b border-white/[0.06] z-20">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-rose-500/70" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/70" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
                </div>
                <div className="flex-1 max-w-sm mx-auto">
                  <div className="h-5 rounded-md bg-white/[0.05] border border-white/[0.05] flex items-center justify-center">
                    <span className="text-[10px] text-slate-500 font-mono">app.breatheesg.com/dashboard</span>
                  </div>
                </div>
              </div>

              <div className="relative w-full h-full pt-12">
                {slides.map((slide, idx) => (
                  <img
                    key={slide.id}
                    src={slide.src}
                    alt={slide.title}
                    className={`absolute inset-0 pt-12 w-full h-full object-cover object-top transition-opacity duration-500 ${
                      current === idx ? 'opacity-100 z-10' : 'opacity-0 z-0'
                    }`}
                  />
                ))}
              </div>

            </div>
          </div>
          
        </div>
      </div>
    </section>
  )
}
