from enum import Enum


class DueDiligenceBQKeys(Enum):
    module_wattage = "Module Wattage"
    module_quantity = "Module Quantity"
    inverter_wattage = "Inverter Wattage"
    inverter_quantity = "Inverter Quantity"
    jan = "January Estimated Production (Year 1)"
    feb = "February Estimated Production (Year 1)"
    mar = "March Estimated Production (Year 1)"
    apr = "April Estimated Production (Year 1)"
    may = "May Estimated Production (Year 1)"
    jun = "June Estimated Production (Year 1)"
    jul = "July Estimated Production (Year 1)"
    aug = "August Estimated Production (Year 1)"
    sep = "September Estimated Production (Year 1)"
    oct = "October Estimated Production (Year 1)"
    nov = "November Estimated Production (Year 1)"
    dec = "December Estimated Production (Year 1)"

    @classmethod
    def list(cls):
        return [option.value for option in list(cls)]


DD_BQ_QUANTITY_KEYS = [
    DueDiligenceBQKeys.module_quantity.name,
    DueDiligenceBQKeys.inverter_quantity.name,
    DueDiligenceBQKeys.module_wattage.name,
    DueDiligenceBQKeys.inverter_wattage.name,
]
DD_YEAR_METRICS_KEYS_VALUES = [
    DueDiligenceBQKeys.jan.value,
    DueDiligenceBQKeys.feb.value,
    DueDiligenceBQKeys.mar.value,
    DueDiligenceBQKeys.apr.value,
    DueDiligenceBQKeys.may.value,
    DueDiligenceBQKeys.jun.value,
    DueDiligenceBQKeys.jul.value,
    DueDiligenceBQKeys.aug.value,
    DueDiligenceBQKeys.sep.value,
    DueDiligenceBQKeys.oct.value,
    DueDiligenceBQKeys.nov.value,
    DueDiligenceBQKeys.dec.value,
]
DD_YEAR_METRICS_KEYS_MONTH_ORDER = [
    DueDiligenceBQKeys.jan.name,
    DueDiligenceBQKeys.feb.name,
    DueDiligenceBQKeys.mar.name,
    DueDiligenceBQKeys.apr.name,
    DueDiligenceBQKeys.may.name,
    DueDiligenceBQKeys.jun.name,
    DueDiligenceBQKeys.jul.name,
    DueDiligenceBQKeys.aug.name,
    DueDiligenceBQKeys.sep.name,
    DueDiligenceBQKeys.oct.name,
    DueDiligenceBQKeys.nov.name,
    DueDiligenceBQKeys.dec.name,
]

DD_BQ_ESTIMATED_GENERATION_FIELD_NAME = "estimated_generation"
