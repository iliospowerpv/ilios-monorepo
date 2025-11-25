from ..common.entities import Device
from ..common.enums import DataProvider
from ..common.params import RetrieveDevicesServiceRequestParams
from .data_providers import also_energy, kmc


def retrieve_devices(params: RetrieveDevicesServiceRequestParams) -> list[Device]:
    match params.data_provider:
        case DataProvider.ALSO_ENERGY:
            return also_energy.retrieve_devices(params.token, params.site_id)
        case DataProvider.KMC:
            return kmc.retrieve_devices(params.token, params.site_id)
        case _:
            data_provider = str(params.data_provider)
            raise NotImplementedError(f"{data_provider=}")
