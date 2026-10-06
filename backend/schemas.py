from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator
from ml.predict import clean_text


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, allow_inf_nan=False)


class Login(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.casefold()


class Register(Login):
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Display name must not be blank")
        return value


class Profile(StrictModel):
    display_name: str = Field(min_length=1, max_length=80)
    clean_name = field_validator("display_name")(Register.clean_name.__func__)


class PasswordChange(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class AccountStatus(StrictModel):
    active: StrictBool


VehicleType = Literal["Car", "Bike", "Scooter"]


class PredictionRequest(StrictModel):
    vehicle_type: VehicleType
    brand: StrictStr = Field(min_length=1, max_length=160)
    model: StrictStr = Field(min_length=1, max_length=160)
    manufacture_year: StrictInt = Field(ge=1900, le=2100)
    km_driven: StrictFloat | StrictInt = Field(ge=0, le=10_000_000)
    engine_capacity_cc: StrictFloat | StrictInt | None = Field(None, ge=0, le=50_000)
    owner_count: StrictInt | None = Field(None, ge=1, le=4)
    motor_power_kw: StrictFloat | StrictInt | None = Field(None, gt=0, le=10_000)
    power_bhp: StrictFloat | StrictInt | None = Field(None, gt=0, le=20_000)
    mileage_kmpl: StrictFloat | StrictInt | None = Field(None, gt=0, le=1000)
    seats: StrictInt | None = Field(None, ge=1, le=9)
    gears: StrictInt | None = Field(None, ge=0, le=6)
    region: Literal['Bagmati', 'Gandaki', 'Karnali', 'Koshi', 'Lumbini', 'Madhesh', 'Sudurpashchim'] | None = None
    city: StrictStr | None = Field(None, max_length=160)
    location_raw: StrictStr | None = Field(None, max_length=160)
    fuel_type: StrictStr | None = Field(None, max_length=160)
    transmission: StrictStr | None = Field(None, max_length=160)
    condition: Literal['Excellent', 'Good', 'Fair', 'Poor'] | None = None
    body_type: StrictStr | None = Field(None, max_length=160)
    insurance_status: StrictStr | None = Field(None, max_length=160)
    color: StrictStr | None = Field(None, max_length=160)
    listing_condition: StrictStr | None = Field(None, max_length=160)

    @field_validator('brand', 'model', 'city', 'color', 'fuel_type', 'vehicle_type', 'region', 'condition',
                     'transmission', 'body_type', 'location_raw', 'insurance_status', 'listing_condition', mode='before')
    @classmethod
    def normalize_text(cls, value, info):
        if not isinstance(value, str):
            return value
        value = clean_text(value)
        if not value and info.field_name not in ('brand', 'model', 'vehicle_type'):
            return None
        if info.field_name in ('vehicle_type', 'region', 'condition'):
            value = value.title()
        return value
