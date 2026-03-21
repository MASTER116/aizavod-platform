import { useState } from 'react'

interface Props {
  title: string
  message: string
  needReason?: boolean
  onConfirm: (reason: string) => void
  onCancel: () => void
  confirmLabel?: string
  confirmColor?: string
}

export function ConfirmDialog({ title, message, needReason, onConfirm, onCancel, confirmLabel = 'Confirm', confirmColor = '#ef4444' }: Props) {
  const [reason, setReason] = useState('')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 max-w-md w-full mx-4" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-zinc-400 text-sm mb-4">{message}</p>
        {needReason && (
          <textarea
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-200 mb-4 resize-none"
            rows={2}
            placeholder="Reason..."
            value={reason}
            onChange={e => setReason(e.target.value)}
          />
        )}
        <div className="flex justify-end gap-3">
          <button className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200" onClick={onCancel}>Cancel</button>
          <button
            className="px-4 py-2 text-sm rounded font-medium text-white"
            style={{ background: confirmColor }}
            onClick={() => onConfirm(reason)}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
