export function LoadingState({ label = 'Carregando...' }: { label?: string }) {
  return <div className="state-box"><span className="loader" />{label}</div>
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="state-box empty"><span aria-hidden="true">◇</span><strong>{title}</strong><p>{description}</p></div>
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="state-box error"><strong>Algo deu errado</strong><p>{message}</p>{retry && <button className="secondary-button" onClick={retry}>Tentar novamente</button>}</div>
}
