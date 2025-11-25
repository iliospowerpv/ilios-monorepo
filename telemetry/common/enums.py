from enum import StrEnum
from typing import Self


class DataProvider(StrEnum):
    ALSO_ENERGY = "also_energy"
    KMC = "kmc"


class PlatformEnvironment(StrEnum):
    UAT = "uat"
    QA = "qa"
    DEV = "dev"

    @classmethod
    def as_list(cls) -> list[Self]:
        return list(cls)


class TelemetryCategory(StrEnum):
    POINTS = "points"
    ALERTS = "alerts"


class PointTag(StrEnum):
    DEVICE_POWER_AC = "device_power_ac"  # kW
    SITE_CELL_TEMPERATURE = "site_cell_temperature"  # °F
    SITE_IRRADIANCE = "site_irradiance"  # W/m²
    SITE_POWER_AC = "site_power_ac"  # kW
