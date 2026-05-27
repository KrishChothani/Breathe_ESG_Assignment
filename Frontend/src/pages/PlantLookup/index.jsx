import { useState, useEffect, useCallback } from 'react'
import { useSelector } from 'react-redux'
import PlantLookupTable from './PlantLookupTable'
import UnresolvedTable from './UnresolvedTable'
import BulkImportPanel from './BulkImportPanel'
import PlantLookupFormModal from './PlantLookupFormModal'
import { exportPlantCSV } from '../../api/plantLookup'

const TABS = [
  { key: 'plants',     label: '🏭 Plant Codes' },
  { key: 'unresolved', label: '⚠️ Unresolved WERKS' },
  { key: 'import',     label: '📥 Bulk Import' },
]

export default function PlantLookupPage() {
  const [activeTab, setActiveTab]     = useState('plants')
  const [showForm, setShowForm]       = useState(false)
  const [editPlant, setEditPlant]     = useState(null)
  const [prefillCode, setPrefillCode] = useState('')
  const [refresh, setRefresh]         = useState(0)

  const triggerRefresh = useCallback(() => setRefresh((r) => r + 1), [])

  const openCreate = (werksCode = '') => {
    setEditPlant(null)
    setPrefillCode(werksCode)
    setShowForm(true)
  }
  const openEdit = (plant) => {
    setEditPlant(plant)
    setPrefillCode('')
    setShowForm(true)
  }
  const closeForm = () => {
    setShowForm(false)
    setEditPlant(null)
    setPrefillCode('')
  }
  const handleSaved = () => {
    closeForm()
    triggerRefresh()
  }

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Plant Code Management</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Map SAP WERKS codes to real locations for accurate emissions calculation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => exportPlantCSV()}
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export CSV
          </button>
          <button
            onClick={() => openCreate()}
            className="btn-primary"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Add Plant Code
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === key
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'plants' && (
        <PlantLookupTable
          refresh={refresh}
          onEdit={openEdit}
          onRefresh={triggerRefresh}
        />
      )}
      {activeTab === 'unresolved' && (
        <UnresolvedTable
          refresh={refresh}
          onAddLookup={openCreate}
        />
      )}
      {activeTab === 'import' && (
        <BulkImportPanel onImported={triggerRefresh} />
      )}

      {/* Form modal */}
      {showForm && (
        <PlantLookupFormModal
          plant={editPlant}
          prefillWerksCode={prefillCode}
          onClose={closeForm}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
