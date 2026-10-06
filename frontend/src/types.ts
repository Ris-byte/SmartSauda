export type VehicleType = 'Car' | 'Bike' | 'Scooter'
export const vehicleTypes: VehicleType[] = ['Car', 'Bike', 'Scooter']
export const modelInputFields = (type: VehicleType) => new Set(['vehicle_type', 'brand', 'model', 'manufacture_year', 'km_driven', 'engine_capacity_cc',
  ...(type === 'Car' ? ['owner_count', 'region', 'fuel_type', 'transmission', 'condition', 'body_type'] : type === 'Scooter' ? ['motor_power_kw'] : [])])
export type CatalogModel = { model: string; training_rows: number; min_year: number; max_year: number;
  constraints: { observed_min_year: number; observed_max_year: number; year_basis: string; fuel_types: string[];
    engine_capacity_cc: [number, number]; motor_power_kw: [number, number] | null; transmissions: string[];
    body_types: string[]; km_driven_max: number; km_per_year_max: number; reference_year: number } }
export type User = { id: string; email: string; display_name: string; role: 'User' | 'Admin'; active: boolean; created_at: string }
export type Warning = { code: string; message: string; field?: string }
export type Specifications = { vehicle_type: VehicleType; brand: string; model: string; manufacture_year: number; km_driven: number; [field: string]: string | number | null }
export type VehicleImage = { is_placeholder: boolean; url: string; attribution_url: string | null; provider: string; reason?: string; match_kind?: 'model' | 'category' | 'render'; depicted_model?: string; author?: string; title?: string; license?: string; license_url?: string; fallback_photo?: VehicleImage }
export type Prediction = {
  id: string; created_at: string; specifications: Specifications; image: VehicleImage;
  result: { predicted_price: number; vehicle_type: VehicleType; model_version: string; currency: string; vehicle_age: number; reference_year?: number;
    warnings: Warning[]; ignored_input_fields: string[]; is_extrapolation: boolean; brand_model_fit_rows: number }
}
export type History = { items: Prediction[]; total: number; limit: number; offset: number }
export type Dashboard = { total_predictions: number; by_type: Record<VehicleType, number>; average_price: number | null; lowest_price: number | null; highest_price: number | null; recent: Prediction[] }
export const money = (value: number, decimals = 0) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: decimals, minimumFractionDigits: decimals }).format(value)
export const date = (value: string) => new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kathmandu' }).format(new Date(value))
