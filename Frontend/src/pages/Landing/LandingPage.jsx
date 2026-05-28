/**
 * LandingPage.jsx — BreatheESG public-facing landing page
 *
 * Route: GET /
 * - Unauthenticated users: renders this marketing page
 * - Authenticated users: redirected to /dashboard by PublicRoute in App.jsx
 *
 * Section order:
 *   Navbar → Hero → TrustBar → Features → HowItWorks →
 *   ProductPreview → ComplianceStrip → Pricing → FinalCTA → Footer
 */
import Navbar          from './sections/Navbar'
import Hero            from './sections/Hero'
import TrustBar        from './sections/TrustBar'
import Features        from './sections/Features'
import HowItWorks      from './sections/HowItWorks'
import ProductPreview  from './sections/ProductPreview'
import ComplianceStrip from './sections/ComplianceStrip'
import FinalCTA        from './sections/FinalCTA'
import Footer          from './sections/Footer'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 overflow-x-hidden font-sans">
      <Navbar />
      <main>
        <Hero />
        <TrustBar />
        <Features />
        <HowItWorks />
        <ProductPreview />
        <ComplianceStrip />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  )
}
