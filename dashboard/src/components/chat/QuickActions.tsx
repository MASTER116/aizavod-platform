interface Props {
  actions: string[]
  onAction: (action: string) => void
  disabled?: boolean
}

export function QuickActions({ actions, onAction, disabled }: Props) {
  if (!actions.length) return null

  return (
    <div className="flex gap-2 px-4 py-2 overflow-x-auto border-t border-zinc-800/50">
      {actions.map(a => (
        <button
          key={a}
          onClick={() => onAction(a)}
          disabled={disabled}
          className="shrink-0 px-3 py-1.5 text-xs rounded-full border border-zinc-700 text-zinc-400 hover:text-[var(--color-zavod-gold)] hover:border-[var(--color-zavod-gold)]/40 transition-colors disabled:opacity-30"
        >
          {a}
        </button>
      ))}
    </div>
  )
}
