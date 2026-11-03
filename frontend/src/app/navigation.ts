export type Route = 'dashboard' | 'assets' | 'asset-detail' | 'operations' | 'notifications' | 'reports' | 'catalogs'

const routeFromHash = (): Route => {
  const route = window.location.hash.replace(/^#\/?/, '')
  if (/^assets\/\d+$/.test(route)) return 'asset-detail'
  return ['dashboard', 'assets', 'operations', 'notifications', 'reports', 'catalogs'].includes(route)
    ? (route as Route)
    : 'dashboard'
}

export const navigation = {
  current: routeFromHash,
  go: (route: Route) => {
    window.location.hash = `/${route === 'asset-detail' ? 'assets' : route}`
  },
  asset: (assetId: number) => { window.location.hash = `/assets/${assetId}` },
  assetId: () => {
    const match = window.location.hash.match(/^#\/?assets\/(\d+)$/)
    return match ? Number(match[1]) : null
  },
}
