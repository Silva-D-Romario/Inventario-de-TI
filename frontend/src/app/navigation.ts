export type Route = 'dashboard' | 'assets' | 'operations' | 'catalogs'

const routeFromHash = (): Route => {
  const route = window.location.hash.replace(/^#\/?/, '')
  return ['dashboard', 'assets', 'operations', 'catalogs'].includes(route)
    ? (route as Route)
    : 'dashboard'
}

export const navigation = {
  current: routeFromHash,
  go: (route: Route) => {
    window.location.hash = `/${route}`
  },
}
