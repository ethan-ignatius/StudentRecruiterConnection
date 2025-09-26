import requests
from django.conf import settings
from .models import CityCoord

STATE_ALIASES = {  # normalize “Georgia”→“GA”
    "georgia":"GA","new york":"NY","california":"CA","texas":"TX","florida":"FL",
    # …add others you use; optional if you already store postal codes
}

def _normalize_city_state(city: str, state: str):
    c = (city or "").strip()
    s = (state or "").strip()
    if len(s) > 2:
        s = STATE_ALIASES.get(s.lower(), s)
    return c, s

def geocode_city_state(city: str, state: str, country: str = "USA"):
    """Return (lat, lng) for City, State, using OSM Nominatim; cached in DB."""
    city, state = _normalize_city_state(city, state)
    if not city or not state:
        return None

    # 1) check local cache
    try:
        cc = CityCoord.objects.get(city__iexact=city, state__iexact=state)
        return cc.lat, cc.lng
    except CityCoord.DoesNotExist:
        pass

    # 2) call Nominatim (respect their policy: set a UA; low volume only)
    q = f"{city}, {state}, {country}"
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": getattr(settings, "GEOCODER_USER_AGENT", "job-board-class-demo/1.0")}
    params  = {"q": q, "format": "json", "limit": 1}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=6)
        r.raise_for_status()
        data = r.json()
        if data:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            CityCoord.objects.create(city=city, state=state, lat=lat, lng=lng)  # cache it
            return lat, lng
    except requests.RequestException:
        pass
    return None
