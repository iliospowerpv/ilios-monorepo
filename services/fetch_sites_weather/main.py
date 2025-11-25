import functions_framework
from .sites_manager import SitesManager


@functions_framework.http
def fetch_sites_weather(request):
    SitesManager().process_sites_weather()
    return "OK"
