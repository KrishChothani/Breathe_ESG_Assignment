/**
 * MemberRow.jsx — Single member row in the members table.
 */

const ROLE_STYLES = {
  ADMIN:   'bg-violet-100 text-violet-700 border border-violet-200',
  ANALYST: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  AUDITOR: 'bg-amber-100 text-amber-700 border border-amber-200',
  VIEWER:  'bg-slate-100 text-slate-600 border border-slate-200',
}

const ROLES = ['ADMIN', 'ANALYST', 'AUDITOR', 'VIEWER']

export default function MemberRow({ member, isAdmin, onRoleChange, onRemove }) {
  const initials = member.user_full_name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || member.user_email[0].toUpperCase()

  return (
    <div className="flex items-center justify-between px-6 py-4 hover:bg-slate-50/50 transition-colors">
      {/* Avatar + name */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="h-9 w-9 rounded-full bg-gradient-to-br from-slate-300 to-slate-400 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-800 truncate">
            {member.user_full_name || member.user_email}
          </p>
          <p className="text-xs text-slate-400 truncate">{member.user_email}</p>
        </div>
      </div>

      {/* Role + joined */}
      <div className="flex items-center gap-4">
        <span className="text-xs text-slate-400 hidden md:block">
          Joined {new Date(member.joined_at).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' })}
        </span>

        {/* Role badge or select */}
        {isAdmin ? (
          <select
            value={member.role}
            onChange={(e) => onRoleChange(member.id, e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700 cursor-pointer hover:border-emerald-300 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-300"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        ) : (
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${ROLE_STYLES[member.role]}`}>
            {member.role}
          </span>
        )}

        {/* Remove button (admin only) */}
        {isAdmin && (
          <button
            onClick={() => onRemove(member.id, member.user_full_name || member.user_email)}
            className="rounded-lg px-2 py-1 text-xs text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors"
            title="Remove member"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  )
}
