import React, { useState } from 'react';
import ReuploadModal from './ReuploadModal';

export default function FailedRowsTable({ rows, onRefresh }) {
  const [reuploadRow, setReuploadRow] = useState(null);

  if (!rows || rows.length === 0) {
    return (
      <div className="card p-8 text-center text-slate-500">
        No failed rows — all ingested data parsed successfully.
      </div>
    );
  }

  return (
    <>
      <div className="card p-0 overflow-hidden relative min-h-[300px]">
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="border-b border-gray-200 bg-slate-50">
                <th className="th">Source</th>
                <th className="th">Filename</th>
                <th className="th">Failed At</th>
                <th className="th">Error Reason</th>
                <th className="th w-24">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="td">
                    <span className="rounded px-1.5 py-0.5 bg-rose-50 text-rose-700 text-xs font-medium">
                      {row.source_type}
                    </span>
                  </td>
                  <td className="td font-mono text-slate-600">{row.filename || '—'}</td>
                  <td className="td text-slate-500">{new Date(row.failed_at).toLocaleString()}</td>
                  <td className="td text-rose-600 max-w-md truncate" title={row.parse_error}>
                    {row.parse_error || 'Unknown error'}
                  </td>
                  <td className="td">
                    <button
                      onClick={() => setReuploadRow(row)}
                      className="rounded px-2.5 py-1 text-xs font-medium bg-emerald-50 hover:bg-emerald-100 text-emerald-700 transition-colors"
                    >
                      Re-upload
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {reuploadRow && (
        <ReuploadModal
          row={reuploadRow}
          onClose={() => setReuploadRow(null)}
          onSuccess={() => {
            setReuploadRow(null);
            onRefresh();
          }}
        />
      )}
    </>
  );
}
