from ..common.entities import Site
from ..common.enums import DataProvider
from ..common.params import RetrieveSitesServiceRequestParams
from .data_providers import also_energy, kmc


def retrieve_sites(params: RetrieveSitesServiceRequestParams) -> list[Site]:
    match params.data_provider:
        case DataProvider.ALSO_ENERGY:
            return also_energy.retrieve_sites(params.token)
        case DataProvider.KMC:
            return kmc.retrieve_sites(params.token)
        case _:
            data_provider = str(params.data_provider)
            raise NotImplementedError(f"{data_provider=}")
