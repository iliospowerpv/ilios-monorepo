"""Native weather domain services (Weather Data Architecture).

W1 introduces the :class:`~app.services.weather.weather_resolver.WeatherResolver`
— a strictly read-only seam that resolves the physics weather inputs of the
expected-performance calc from EXISTING V2 telemetry rollups while carrying W0
provenance. It adds no external provider, secret, BigQuery, or Firestore
dependency.
"""
