import requests
import polyline
from typing import List
import math

class DistanceService:
    def __init__(self, geoapify_key: str):
        self.api_key = geoapify_key
        self._geo_cache = {}       # place -> (lat, lon)
        self._distance_cache = {}  # (placeA, placeB) -> km

    # GEOCODING 
    def geocode(self, place: str):

        if place in self._geo_cache:
            return self._geo_cache[place]

        url = "https://api.geoapify.com/v1/geocode/search"
        params = {"text": place, "apiKey": self.api_key}

        r = requests.get(url, params=params).json()
        
        if not r.get("features"):
            return None

        lon, lat = r["features"][0]["geometry"]["coordinates"]
        self._geo_cache[place] = (lat, lon)
        return lat, lon
    import math

    def haversine_km(self, lat1, lon1, lat2, lon2):
        R = 6371.0  # Earth radius in km

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)

        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        )

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c


    # STRAIGHT-LINE (HAVERSINE) DISTANCE
    def driving_distance(self, origin: str, destination: str) -> float | None:
        key = tuple(sorted((origin, destination)))
        if key in self._distance_cache:
            return self._distance_cache[key]

        o = self.geocode(origin)
        d = self.geocode(destination)

        if not o or not d:
            return None

        lat1, lon1 = o[1], o[0]
        lat2, lon2 = d[1], d[0]

        km = self.haversine_km(lat1, lon1, lat2, lon2)
        self._distance_cache[key] = km
        return km

    # PRECOMPUTE ALL DISTANCES
    def _build_distance_matrix(self, places: List[str]):
        for i in range(len(places)):
            for j in range(i + 1, len(places)):
                self.driving_distance(places[i], places[j])

    # NEAREST NEIGHBOUR OPTIMIZATION
    def get_optimized_route(self, places: List[str]) -> List[str]:
        if len(places) <= 2:
            return places

        # Precompute all pairwise distances once
        self._build_distance_matrix(places)

        remaining = [p.strip() for p in places]
        route = [remaining.pop(0)]

        while remaining:
            current = route[-1]

            nearest_place = None
            nearest_distance = float("inf")

            for place in remaining:
                key = tuple(sorted((current, place)))
                distance = self._distance_cache.get(key, float("inf"))

                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_place = place

            if nearest_place is None:
                # Fallback: just take the next available place
                nearest_place = remaining[0]
            
            route.append(nearest_place)
            remaining.remove(nearest_place)

        return route


def get_route(
    coordinates: list,
    api_key: str,
    max_distance_km: float = 500
):

    if len(coordinates) < 2:
        return {
            "distance_km": 0,
            "duration_min": 0,
            "steps": [],
            "geometry": []
        }

    # Prepare fallback geometry (start → end)
    start_lon, start_lat = coordinates[0]
    end_lon, end_lat = coordinates[-1]
    fallback_geometry = [(start_lat, start_lon), (end_lat, end_lon)]

    # Geoapify expects: lat,lon|lat,lon
    waypoints = "|".join(
        f"{lat},{lon}" for lon, lat in coordinates
    )

    url = "https://api.geoapify.com/v1/routing"
    params = {
        "waypoints": waypoints,
        "mode": "drive",
        "details": "instruction_details",
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return {
                "distance_km": 0,
                "duration_min": 0,
                "steps": [],
                "geometry": fallback_geometry
            }

        data = response.json()

        if not data.get("features"):
            return {
                "distance_km": 0,
                "duration_min": 0,
                "steps": [],
                "geometry": fallback_geometry
            }

        route = data["features"][0]
        props = route["properties"]

        distance_m = props.get("distance", 0)
        duration_s = props.get("time", 0)

        distance_km = distance_m / 1000
        duration_min = duration_s / 60

        decoded_coords = polyline.decode(route["geometry"])

        geometry = (
            [decoded_coords[0], decoded_coords[-1]]
            if distance_km > max_distance_km
            else decoded_coords
        )

        steps = []
        legs = props.get("legs", [])
        if legs:
            for step in legs[0].get("steps", []):
                steps.append({
                    "instruction": step.get("instruction"),
                    "distance_m": step.get("distance"),
                    "duration_s": step.get("time")
                })

        return {
            "distance_km": distance_km,
            "duration_min": duration_min,
            "steps": steps,
            "geometry": geometry
        }

    except Exception:
        # Absolute last-resort fallback
        return {
            "distance_km": 0,
            "duration_min": 0,
            "steps": [],
            "geometry": fallback_geometry
        }

# REVERSE GEOCODING 
def reverse_geocode(lat, lon, api_key):
    r = requests.get(
        "https://api.geoapify.com/v1/geocode/reverse",
        params={
            "lat": lat,
            "lon": lon,
            "apiKey": api_key
        }
    ).json()

    if not r.get("features"):
        return "Unknown location"

    props = r["features"][0]["properties"]
    return (
        props.get("city")
        or props.get("town")
        or props.get("village")
        or props.get("formatted")
    )
