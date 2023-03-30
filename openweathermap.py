import os
from typing import List, Dict, Any

import requests
from PIL import Image


class OpenWeatherMap:
    API_BASE = "https://api.openweathermap.org"
    API_PARAMS = "?units=metric&lat={lat}&lon={lon}&appid={api_key}"
    CURRENT_WEATHER_API = API_BASE + "/data/2.5/weather" + API_PARAMS
    FORECAST_API = API_BASE + "/data/2.5/forecast" + API_PARAMS
    GEOCODING_API = (
        API_BASE + "/geo/1.0/direct?q={location}&limit=1&appid={api_key}"
    )

    def __init__(self):
        self.lat = float(os.environ.get("LATITUDE") or input("Latitude: "))
        self.lon = float(os.environ.get("LONGITUDE") or input("Longitude: "))
        self.api_key = os.environ.get("WEATHER_API_KEY") or input("API Key: ")

    def current(self) -> Dict[str, Any]:
        url = self.CURRENT_WEATHER_API.format(
            lat=self.lat, lon=self.lon, api_key=self.api_key
        )
        resp = requests.get(url, timeout=1)
        assert resp.status_code == 200
        data = resp.json()
        return data

    def forecasts(self) -> List[Dict[str, Any]]:
        url = self.FORECAST_API.format(
            lat=self.lat, lon=self.lon, api_key=self.api_key
        )
        resp = requests.get(url, timeout=1)
        assert resp.status_code == 200
        data = resp.json()
        forecasts = data["list"]
        return forecasts

    @classmethod
    def icon(cls, code: str) -> Image.Image:
        return Image.open(
            os.path.join(os.path.dirname(__file__), "icons", f"{code}@2x.png")
        )
