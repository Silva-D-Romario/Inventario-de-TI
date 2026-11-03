export type UserRole = 'USER' | 'TECHNICIAN' | 'ADMIN'

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: UserRole
  role_display: string
  is_active: boolean
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface NamedReference {
  id: number
  name: string
  is_active: boolean
}

export interface Category extends NamedReference {
  description: string
}

export interface Sector extends NamedReference {
  location: string
}

export interface AssetStatus extends NamedReference {
  code: string
  color: string
}

export interface Asset {
  id: number
  public_id: string
  asset_tag: string
  name: string
  category: number
  category_name: string
  sector: number
  sector_name: string
  status: number
  status_name: string
  status_color: string
  responsible: number | null
  responsible_name: string | null
  qr_code_url: string
  serial_number: string | null
  manufacturer: string
  model: string
  acquisition_date: string | null
  purchase_value: string | null
  notes: string
  created_by_username: string | null
  created_at: string
  updated_at: string
}

export interface ResponsiblePerson {
  id: number
  name: string
  email: string
  employee_id: string | null
  phone: string
  sector: number
  sector_name: string
  is_active: boolean
}

export interface Loan {
  id: number
  asset: number
  asset_tag: string
  borrower: number
  borrower_name: string
  loaned_at: string
  expected_return_date: string
  returned_at: string | null
  is_active: boolean
  notes: string
}

export interface Maintenance {
  id: number
  asset: number
  asset_tag: string
  maintenance_type: 'PREVENTIVE' | 'CORRECTIVE'
  maintenance_type_display: string
  status: 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
  status_display: string
  description: string
  provider: string
  started_at: string
  completed_at: string | null
  cost: string | null
  resolution_notes: string
  is_active: boolean
}

export interface Warranty {
  id: number
  asset: number
  asset_tag: string
  provider: string
  contract_number: string
  start_date: string
  end_date: string
  coverage_notes: string
  is_active: boolean
}

export interface AssetCost {
  id: number
  asset: number
  asset_tag: string
  maintenance: number | null
  cost_type: 'PURCHASE' | 'MAINTENANCE' | 'LICENSE' | 'OTHER'
  cost_type_display: string
  amount: string
  occurred_on: string
  description: string
}

export interface AssetAttachment {
  id: number
  asset: number
  asset_tag: string
  maintenance: number | null
  file_name: string
  download_url: string
  description: string
  uploaded_by_username: string | null
  created_at: string
}

export interface AssetMovement {
  id: number
  asset: number
  asset_tag: string
  movement_type: string
  movement_type_display: string
  from_sector: number | null
  from_sector_name: string | null
  to_sector: number | null
  to_sector_name: string | null
  responsible: number | null
  responsible_name: string | null
  performed_by_username: string | null
  notes: string
  created_at: string
}

export interface Notification {
  id: number
  alert_type: string
  alert_type_display: string
  title: string
  message: string
  resource_type: string
  resource_id: number
  is_read: boolean
  read_at: string | null
  created_at: string
}

export interface DashboardSummary {
  total_assets: number
  total_purchase_value: string
  active_loans: number
  overdue_loans: number
  open_maintenances: number
  maintenance_cost_current_year: string
  warranties_expiring_in_30_days: number
}

export interface DistributionItem {
  key: number
  label: string
  total: number
}

export interface LatestMovement {
  id: number
  asset_tag: string
  asset_name: string
  movement_type: string
  movement_type_display: string
  performed_by: string | null
  created_at: string
}

export interface DashboardData {
  generated_at: string
  summary: DashboardSummary
  assets_by_status: DistributionItem[]
  assets_by_category: DistributionItem[]
  assets_by_sector: DistributionItem[]
  cost_trend: Array<{ month: string; total: string }>
  latest_movements: LatestMovement[]
}
