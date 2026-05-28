/**
 * FinalCTA.jsx — Full-width gradient call-to-action band (Alternating Dark Theme)
 */
import { Link } from 'react-router-dom'

export default function FinalCTA() {
  return (
    <section className="py-24 px-6 relative overflow-hidden bg-slate-900">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:32px_32px]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-blue-600/20 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        <h2 className="text-4xl sm:text-5xl md:text-6xl font-black text-white mb-6 tracking-tight leading-tight">
          Ready to make your
          <br />
          <span className="text-blue-400">
            carbon data auditable?
          </span>
        </h2>
        <p className="text-lg text-slate-400 mb-10 max-w-xl mx-auto font-medium">
          Join enterprises already using BreatheESG to file SEBI BRSR Core disclosures
          with confidence. Set up in minutes.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/login"
            className="group inline-flex items-center gap-2.5 px-8 py-4 bg-blue-600 text-white font-bold rounded-xl text-base shadow-xl shadow-blue-900/30 hover:shadow-blue-900/50 hover:opacity-95 hover:-translate-y-0.5 transition-all"
          >
            Start Your Free Trial
            <svg className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </Link>
          <a
            href="mailto:team@breatheesg.com"
            className="inline-flex items-center gap-2 px-8 py-4 border-2 border-slate-700 text-white hover:bg-slate-800 font-medium rounded-xl transition-all text-base"
          >
            Talk to Sales
          </a>
        </div>

        <p className="text-sm text-slate-500 mt-8 font-medium">
          No credit card required · SEBI BRSR ready · Cancel anytime
        </p>
      </div>
    </section>
  )
}
