import { ROW_STATUS } from '../utils/constants'

const STATUS_CONFIG = {
  [ROW_STATUS.PENDING]:  { cls: 'bg-gray-100 text-gray-700',    label: 'Pending'  },
  [ROW_STATUS.FLAGGED]:  { cls: 'bg-amber-100 text-amber-800',  label: 'Flagged'  },
  [ROW_STATUS.APPROVED]: { cls: 'bg-emerald-100 text-emerald-800', label: 'Approved' },
  [ROW_STATUS.REJECTED]: { cls: 'bg-rose-100 text-rose-800',    label: 'Rejected' },
  [ROW_STATUS.LOCKED]:   { cls: 'bg-blue-100 text-blue-800',    label: 'Locked'   },
}

export default function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? { cls: 'bg-gray-100 text-gray-500', label: status }
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.cls}`}>
      {status === ROW_STATUS.FLAGGED && (
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd"/>
        </svg>
      )}
      {status === ROW_STATUS.LOCKED && (
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd"/>
        </svg>
      )}
      {cfg.label}
    </span>
  )
}
