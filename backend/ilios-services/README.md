# Ilios Services


## Services:

### fetch_sites_weather
The service is implemented as cloud function to be scheduled cron job with specified interval  
and fetch information about site weather from [weather provider](https://weatherstack.com/documentation).

Cloud function uses app_values_creds secrets that are stored as .yaml file and are parsed to the
function settings. File path is stored at common/settings.py -> ENV_VARIABLES_FILE
