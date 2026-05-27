import React, { useEffect, useState } from 'react';
import api from '../../api/client';
import CommentsPanel from './CommentsPanel';

const AuditLogDrawer = ({ row, source, onClose }) => {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        if (row) {
            api.get(`ingestion/audit-logs/?row_id=${row.id}`)
                .then(res => setLogs(res.data.results || res.data))
                .catch(console.error);
        }
    }, [row]);

    if (!row) return null;

    return (
        <div className="fixed inset-0 z-50 flex justify-end bg-black bg-opacity-50">
            <div className="w-1/3 bg-white h-full shadow-lg flex flex-col">
                <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                    <h2 className="text-xl font-semibold">Audit Trail</h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-black">✖</button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
                    <div>
                        <h3 className="font-medium text-gray-800 border-b pb-2 mb-4">Chronological History</h3>
                        {(!logs || logs.length === 0) ? (
                            <p className="text-sm text-gray-500">No logs found.</p>
                        ) : (
                            <div className="space-y-4">
                                {logs.map(log => (
                                    <div key={log.id} className="text-sm border-l-2 border-blue-500 pl-3">
                                        <div className="flex justify-between text-gray-500 mb-1 text-xs">
                                            <span>{new Date(log.performed_at).toLocaleString()}</span>
                                            <span className="font-medium text-gray-700">
                                                {log.performed_by_details ? `${log.performed_by_details.first_name} ${log.performed_by_details.last_name}` : 'System'}
                                            </span>
                                        </div>
                                        <div className="font-semibold">{log.action}</div>
                                        {log.note && <div className="text-gray-600 mt-1">{log.note}</div>}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    
                    <div className="border-t pt-4">
                        <h3 className="font-medium text-gray-800 border-b pb-2 mb-4">Auditor Comments</h3>
                        <CommentsPanel row={row} source={source} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AuditLogDrawer;
