import azure.functions as func
import json
import logging
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def get_weather_data(lat, lon, api_key):
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={lat},{lon}"
    resp = requests.get(url, timeout=10).json()
    return {
        "temp_c": resp.get("current", {}).get("temp_c", 28.0),
        "status": resp.get("current", {}).get("condition", {}).get("text", "Partly cloudy")
    }

def get_maps_duration(start_lat, start_lon, end_lat, end_lon, api_key):
    maps_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{start_lat},{start_lon}",
        "destinations": f"{end_lat},{end_lon}",
        "departure_time": "now",
        "key": api_key
    }
    resp = requests.get(maps_url, params=params, timeout=10).json()
    try:
        elem = resp["rows"][0]["elements"][0]
        duration_sec = elem["duration_in_traffic"]["value"]
        distance_m = elem["distance"]["value"]
        return {
            "duration_min": round(duration_sec / 60, 2),
            "distance_km": round(distance_m / 1000, 2)
        }
    except:
        return {"duration_min": 0, "distance_km": 0}

@app.route(route="WeatherTrafficFunction", methods=["POST"])
def WeatherTrafficFunction(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # ✅ Parse JSON body
        body = req.get_json()
        logging.info('Python HTTP trigger function processed a request.')
        logging.info(body)
        maps_key = body.get("MAPS_API_KEY")
        weather_key = body.get("WEATHER_API_KEY")
        routes = body.get("routes", [])

        enriched_routes = []

        for route in routes:
            origin_lat = route.get("origin_lat")
            origin_lon = route.get("origin_lon")
            dest_lat = route.get("dest_lat")
            dest_lon = route.get("dest_lon")

            # ✅ Call WeatherAPI + Google Maps
            weather = get_weather_data(origin_lat, origin_lon, weather_key)
            traffic = get_maps_duration(origin_lat, origin_lon, dest_lat, dest_lon, maps_key)

            # ✅ Merge into route dict
            route.update({
                "weather": weather,
                "traffic": traffic
            })
            enriched_routes.append(route)

        return func.HttpResponse(
            json.dumps(enriched_routes),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
