from ..common.enums import DataProvider
from ..common.params import VerifyTokenServiceRequestParams
from .data_providers import also_energy, kmc


def verify_token(params: VerifyTokenServiceRequestParams) -> bool:
    match params.data_provider:
        case DataProvider.ALSO_ENERGY:
            return also_energy.verify_token(params.token)
        case DataProvider.KMC:
            return kmc.verify_token(params.token)
        case _:
            data_provider = str(params.data_provider)
            raise NotImplementedError(f"{data_provider=}")
