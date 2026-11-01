const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const dateFormatter = new Intl.DateTimeFormat('pt-BR')
const dateTimeFormatter = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short',
  timeStyle: 'short',
})

export const formatCurrency = (value: string | number | null) =>
  currencyFormatter.format(Number(value ?? 0))

export const formatDate = (value: string | null) =>
  value ? dateFormatter.format(new Date(`${value}T12:00:00`)) : 'Não informada'

export const formatDateTime = (value: string) => dateTimeFormatter.format(new Date(value))

export const initials = (name: string) => {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  return `${parts.at(0)?.[0] ?? 'U'}${parts.length > 1 ? parts.at(-1)?.[0] ?? '' : ''}`.toUpperCase()
}
