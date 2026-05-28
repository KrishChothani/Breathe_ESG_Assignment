/**
 * Footer.jsx — Dark enterprise footer
 */
import { Link } from 'react-router-dom'

const footerLinks = {
  Product: [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Compliance', href: '#compliance' },
  ],
  Platform: [
    { label: 'Scope 1 Tracking', href: '#features' },
    { label: 'Scope 2 Tracking', href: '#features' },
    { label: 'Scope 3 Travel', href: '#features' },
    { label: 'BRSR Core Reports', href: '#features' },
  ],
  Resources: [
    { label: 'Documentation', href: '#' },
    { label: 'SEBI BRSR Guide', href: '#' },
    { label: 'GHG Protocol Primer', href: '#' },
    { label: 'API Reference', href: '#' },
  ],
  Legal: [
    { label: 'Privacy Policy', href: '#' },
    { label: 'Terms of Service', href: '#' },
    { label: 'Data Processing', href: '#' },
    { label: 'Security', href: '#' },
  ],
}

export default function Footer() {
  return (
    <footer className="border-t border-slate-700 pt-16 pb-8 px-6 bg-slate-900">
      <div className="max-w-7xl mx-auto">
        {/* Top row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-10 mb-14">
          {/* Brand */}
          <div className="col-span-2 sm:col-span-3 lg:col-span-1">
            <Link to="/" className="flex items-center gap-2 mb-4 group w-fit">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-500/20">
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20" width="16" height="16">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                </svg>
              </div>
              <span className="text-white font-bold text-base tracking-tight">BreatheESG</span>
            </Link>
            <p className="text-xs text-slate-400 leading-relaxed max-w-[200px] font-medium">
              Enterprise carbon accounting platform for SEBI BRSR Core compliance.
            </p>
            <div className="flex gap-3 mt-5">
              {['twitter', 'linkedin', 'github'].map((social) => (
                <a
                  key={social}
                  href="#"
                  className="w-8 h-8 rounded-lg border border-slate-700 bg-slate-800 flex items-center justify-center text-slate-400 hover:text-blue-400 hover:border-blue-500/50 transition-all shadow-sm"
                >
                  <span className="sr-only">{social}</span>
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
                  </svg>
                </a>
              ))}
            </div>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([group, links]) => (
            <div key={group}>
              <h3 className="text-xs font-bold text-white uppercase tracking-widest mb-4">{group}</h3>
              <ul className="space-y-2.5">
                {links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      className="text-xs text-slate-400 hover:text-blue-400 font-medium transition-colors"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom row */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-6 border-t border-slate-700">
          <p className="text-xs text-slate-500 font-medium">
            © {new Date().getFullYear()} BreatheESG. Enterprise Carbon Accounting Platform.
          </p>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wide">Systems operational</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
