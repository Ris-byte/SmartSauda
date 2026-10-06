"""Label-free catalog coverage and versioned application support limits."""

REFERENCE_YEAR = 2026
PROVINCES = ("Bagmati", "Gandaki", "Karnali", "Koshi", "Lumbini", "Madhesh", "Sudurpashchim")
CONDITIONS = ("Excellent", "Good", "Fair", "Poor")
KM_LIMITS = {"Car": 220000, "Bike": 500000, "Scooter": 190000}
ENGINE_LIMITS = {"Car": {"Petrol": [796, 1999], "Diesel": [2179, 2755], "Electric": [0, 0]},
                 "Bike": {"Petrol": [80, 803]}, "Scooter": {"Petrol": [102, 160], "Electric": [0, 0]}}
CAR_BODY_TYPES = {
    'BYD': {'Atto 3': 'SUV', 'Dolphin': 'Hatchback'},
    'Honda': {'Amaze': 'Sedan', 'City': 'Sedan'},
    'Hyundai': {'Creta': 'SUV', 'Grand i10': 'Hatchback', 'i10': 'Hatchback', 'i20': 'Hatchback', 'Verna': 'Sedan'},
    'Kia': {'Seltos': 'SUV', 'Sonet': 'SUV', 'Sportage': 'SUV'},
    'Mahindra': {'Scorpio': 'SUV', 'XUV500': 'SUV'},
    'Maruti Suzuki': {'Alto': 'Hatchback', 'Swift': 'Hatchback', 'Wagon R': 'Hatchback'},
    'Nissan': {'Magnite': 'SUV'}, 'Tata': {'Nexon': 'SUV'},
    'Toyota': {'Corolla': 'Sedan', 'Fortuner': 'SUV', 'RAV4': 'SUV'},
    'Volkswagen': {'Polo': 'Hatchback'},
}


def body_types(brand, model):
    value = CAR_BODY_TYPES.get(brand, {}).get(model)
    return [value] if value else []


def build_catalog(rows, vehicle_type):
    """Use all approved descriptions, but count fitting support separately. No price used."""
    rows = rows.loc[rows.vehicle_type == vehicle_type]
    type_min = int(rows.manufacture_year.min())
    catalog = []
    for (brand, model), subset in rows.groupby(["brand", "model"]):
        low, high = int(subset.manufacture_year.min()), int(subset.manufacture_year.max())
        singleton = low == high
        fuels = sorted(subset.fuel_type.dropna().unique().tolist())
        if not fuels:
            fuels = ["Electric" if subset.motor_power_kw.notna().any() else "Petrol"]
        fit_count = int(subset.partition.ne("test").sum()) if "partition" in subset else len(subset)
        catalog.append({"brand": brand, "model": model, "training_rows": fit_count,
                        "min_year": max(type_min, low - int(singleton)),
                        "max_year": min(REFERENCE_YEAR, high + int(singleton)),
                        "constraints": {"observed_min_year": low, "observed_max_year": high,
                            "year_basis": "observed_single_year_padded" if singleton else "observed_range",
                            "catalog_rows": len(subset), "fuel_types": fuels,
                            "engine_capacity_cc": ENGINE_LIMITS[vehicle_type][fuels[0]],
                            "motor_power_kw": [0.35, 3.0] if vehicle_type == "Scooter" and fuels == ["Electric"] else None,
                            "transmissions": ["Manual", "Automatic"] if vehicle_type == "Car" else
                                ["Manual"] if vehicle_type == "Bike" else ["Automatic"],
                            "body_types": body_types(brand, model) if vehicle_type == "Car" else [],
                            "km_driven_max": KM_LIMITS[vehicle_type], "km_per_year_max": 44000,
                            "reference_year": REFERENCE_YEAR}})
    return catalog
