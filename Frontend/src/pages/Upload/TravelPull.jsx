import { useState } from 'react'
import { pullTravelData } from '../../api/ingestion'

export default function TravelPull({ onSuccess }) {
  const [creds, setCreds] = useState({ client_id: '', client_secret: '', trip_ids: [] })
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const handlePull = async () => {
    setStatus('loading'); setError('')
    try {
      await pullTravelData(creds); setStatus('done'); onSuccess?.()
    } catch (err) {
      setStatus('error'); setError(err.response?.data?.detail ?? 'API pull failed.')
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl bg-blue-50 border border-blue-200 px-4 py-3 flex items-start gap-3">
        <svg className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd"/>
        </svg>
        <p className="text-xs text-blue-700">
          Navan credentials are used for a single API sync and are never stored. The OAuth token expires after the session.
        </p>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Navan Client ID</label>
          <input type="text" className="input-field" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            value={creds.client_id} onChange={(e) => setCreds({ ...creds, client_id: e.target.value })} />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Navan Client Secret</label>
          <input type="password" className="input-field" placeholder="••••••••••••••••"
            value={creds.client_secret} onChange={(e) => setCreds({ ...creds, client_secret: e.target.value })} />
        </div>
      </div>

      {status === 'done' && <p className="text-xs text-emerald-600 font-medium">✓ Navan sync successful — travel entries queued for normalisation.</p>}
      {status === 'error' && <p className="text-xs text-rose-600">{error}</p>}

      <button
        className="btn-primary"
        onClick={handlePull}
        disabled={!creds.client_id || !creds.client_secret || status === 'loading'}
      >
        {status === 'loading' ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            Syncing from Navan…
          </>
        ) : 'Sync Navan Travel Data'}
      </button>
    </div>
  )
}
