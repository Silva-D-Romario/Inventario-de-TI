import type { ReactNode } from 'react'

interface ModalProps {
  title: string
  eyebrow: string
  onClose: () => void
  children: ReactNode
}

export function Modal({ title, eyebrow, onClose, children }: ModalProps) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose() }}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="modal-heading">
          <div><p className="eyebrow">{eyebrow}</p><h2 id="modal-title">{title}</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Fechar">×</button>
        </div>
        {children}
      </section>
    </div>
  )
}
