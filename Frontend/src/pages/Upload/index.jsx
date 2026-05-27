import SAPUploader from './SAPUploader'
import UtilityUploader from './UtilityUploader'
import TravelPull from './TravelPull'

const SOURCES = [
  {
    key: 'sap',
    label: 'SAP Flat File',
    description: 'ME2M / MB51 export from SAP Materials Management. Supports DD.MM.YYYY and YYYYMMDD date formats, German header variants, and MEINS unit codes (L, KG, TO, GAL).',
    icon: '📦',
    accent: 'emerald',
    component: SAPUploader,
  },
  {
    key: 'utility',
    label: 'Utility Portal CSV',
    description: 'Multi-meter electricity/gas billing exports. Billing periods crossing calendar months are pro-rated automatically. Supports kWh and kVAh, peak/off-peak tariff bands.',
    icon: '⚡',
    accent: 'amber',
    component: UtilityUploader,
  },
  {
    key: 'travel',
    label: 'Concur Travel API',
    description: 'Pull expense reports directly from the Concur v3 API. Flight distances are computed via Haversine from IATA codes. Hotel, Taxi, Rail and Car Rental expense types supported.',
    icon: '✈️',
    accent: 'blue',
    component: TravelPull,
  },
]

const ACCENT_HEADER = {
  emerald: 'border-t-4 border-emerald-500',
  amber: 'border-t-4 border-amber-400',
  blue: 'border-t-4 border-blue-500',
}

export default function Upload() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-800">Upload Data Sources</h2>
        <p className="text-sm text-slate-500 mt-1">Upload files or sync from external APIs. Each source is parsed, normalised, and queued for analyst review.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {SOURCES.map(({ key, label, description, icon, accent, component: SourceComponent }) => (
          <div key={key} className={`card ${ACCENT_HEADER[accent]} flex flex-col gap-4`}>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xl">{icon}</span>
                <h3 className="text-sm font-semibold text-slate-800">{label}</h3>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">{description}</p>
            </div>
            <div className="border-t border-gray-100 pt-4">
              <SourceComponent />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
