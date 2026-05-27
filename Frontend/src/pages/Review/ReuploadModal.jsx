import React, { useState } from 'react';

export default function ReuploadModal({ row, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [jsonPayload, setJsonPayload] = useState('{\n  // edit raw payload here\n}');

  // This is a dummy implementation of the save logic. 
  // In a real scenario, this would call a backend endpoint to re-process the payload/file.
  const handleSave = async () => {
    setLoading(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 800));
    setLoading(false);
    onSuccess();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">
            Re-upload {row.source_type} Data
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="p-6 overflow-y-auto">
          <div className="mb-6">
            <h4 className="text-sm font-medium text-slate-700 mb-1">Error Reason</h4>
            <div className="p-3 bg-rose-50 text-rose-700 rounded-lg text-sm border border-rose-100">
              {row.parse_error || 'Unknown error'}
            </div>
          </div>

          {row.source_type === 'SAP' && (
            <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:bg-slate-50 transition-colors cursor-pointer">
              <div className="text-slate-400 mb-2">📁</div>
              <p className="text-sm font-medium text-slate-700">Upload new .csv / .txt file</p>
              <p className="text-xs text-slate-500 mt-1">Drag and drop or click to browse</p>
            </div>
          )}

          {row.source_type === 'UTILITY' && (
            <div className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:bg-slate-50 transition-colors cursor-pointer">
              <div className="text-slate-400 mb-2">📄</div>
              <p className="text-sm font-medium text-slate-700">Upload new Utility PDF</p>
              <p className="text-xs text-slate-500 mt-1">Drag and drop or click to browse</p>
            </div>
          )}

          {row.source_type === 'TRAVEL' && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-slate-700">Raw JSON Payload</h4>
              </div>
              <textarea
                value={jsonPayload}
                onChange={(e) => setJsonPayload(e.target.value)}
                className="w-full h-64 p-4 font-mono text-xs bg-slate-900 text-emerald-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                spellCheck="false"
              />
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 bg-slate-50 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors disabled:opacity-50"
          >
            {loading ? 'Processing...' : row.source_type === 'TRAVEL' ? 'Fix & Resubmit' : 'Upload & Process'}
          </button>
        </div>
      </div>
    </div>
  );
}
