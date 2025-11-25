from ..common.entities import DeviceInfo
from ..common.enums import DataProvider
from ..common.params import RetrieveDeviceInfoServiceRequestParams
from .data_providers import also_energy, kmc


def retrieve_device_info(params: RetrieveDeviceInfoServiceRequestParams) -> DeviceInfo:
    match params.data_provider:
        case DataProvider.ALSO_ENERGY:
            return also_energy.retrieve_device_info(params.token, params.site_id, params.device_id)
        case DataProvider.KMC:
            return kmc.retrieve_device_info(params.token, params.site_id, params.device_id)
        case _:
            data_provider = str(params.data_provider)
            raise NotImplementedError(f"{data_provider=}")
