# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import re
from typing import Any, Optional
from urllib.parse import parse_qs

from fastapi import FastAPI, Header, HTTPException, Query, Request

app = FastAPI()


@app.post("/calculator/sum")
async def sum_numbers(request: Request) -> Any:
    data = await request.json()
    if "a" not in data or "b" not in data:
        raise HTTPException(status_code=422, detail="parameter(s) missing")
    a = int(data.get("a", "0"))
    b = int(data.get("b", "0"))
    summation = a + b
    return {"result": summation}


@app.post("/calculator/sum_multiply")
async def sum_multiply_numbers(request: Request) -> Any:
    data = await request.json()
    if "a" not in data or "b" not in data:
        raise HTTPException(status_code=422, detail="parameter(s) missing")
    a = int(data.get("a", "0"))
    b = int(data.get("b", "0"))
    return {"sum": a + b, "product": a * b}


@app.post("/calculator/exponential")
async def exponential_of_numbers(request: Request) -> Any:
    data = await request.json()
    if "a" not in data or "b" not in data:
        raise HTTPException(status_code=422, detail="parameter(s) missing")
    a = int(data.get("a", "0"))
    b = int(data.get("b", "0"))
    exponential = a**b
    return {"result": exponential}


@app.post("/animalFinder")
async def animal_finder(request: Request) -> Any:
    data = await request.json()
    mapping = {"China": "Panda", "Morocco": "Atlas Lion"}
    if "country" not in data:
        raise HTTPException(status_code=422, detail="Parameter 'country' is required")
    if data["country"] not in mapping:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"animal": mapping[data["country"]]}


@app.post("/findCountry")
async def find_country(request: Request) -> Any:
    data = await request.json()
    mapping = {"Africa": "Morocco", "America": "Canada"}
    if "continent" not in data:
        raise HTTPException(status_code=422, detail="Parameter 'continent' is required")
    if data["continent"] not in mapping:
        raise HTTPException(status_code=404, detail="Continent not found")
    return {"country": mapping[data["continent"]]}


async def _require_content_type(request: Request, expected_substring: str) -> None:
    ct = (request.headers.get("content-type") or "").lower()
    if expected_substring not in ct:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported Media Type. Expected Content-Type to include '{expected_substring}'",
        )


async def _extract_city_json_nested(request: Request) -> str:
    # Strict: JSON body with object containing location.city
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=415, detail="Expected application/json body")
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Expected JSON object")
    loc = data.get("location")
    if not isinstance(loc, dict):
        raise HTTPException(status_code=422, detail="Expected 'location' object in JSON")
    city = loc.get("city")
    if not isinstance(city, (str, int, float)):
        raise HTTPException(
            status_code=422, detail="Expected 'location.city' as string/number in JSON"
        )
    return str(city)


async def _extract_city_json_top_level(request: Request) -> str:
    # Strict: JSON body with object containing top-level city only
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=415, detail="Expected application/json body")
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Expected JSON object")
    city = data.get("city")
    if not isinstance(city, (str, int, float)):
        raise HTTPException(
            status_code=422, detail="Expected top-level 'city' as string/number in JSON"
        )
    return str(city)


async def _extract_city_json_array(request: Request) -> str:
    # Strict: JSON body with array, second element is an object with 'location' as string
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=415, detail="Expected application/json body")
    if not isinstance(data, list) or len(data) < 2:
        raise HTTPException(
            status_code=422, detail="Expected JSON array with at least two elements"
        )
    elem = data[1]
    if not isinstance(elem, dict):
        raise HTTPException(status_code=422, detail="Expected second array element to be an object")
    loc = elem.get("location")
    if not isinstance(loc, (str, int, float)):
        raise HTTPException(
            status_code=422, detail="Expected 'location' as string/number in second element"
        )
    return str(loc)


async def _extract_city_form(request: Request) -> str:
    # Strict: application/x-www-form-urlencoded with a 'city' field
    await _require_content_type(request, "application/x-www-form-urlencoded")
    raw = await request.body()
    try:
        text = raw.decode("utf-8", errors="strict")
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid form body encoding")
    try:
        q = parse_qs(text, keep_blank_values=True)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid form body")
    vals = q.get("city")
    if not vals or len(vals) == 0:
        raise HTTPException(status_code=422, detail="Missing 'city' in form body")
    return str(vals[0])


async def _extract_city_plain_text(request: Request) -> str:
    # Strict: plain text body containing 'city: <value>' pattern, reject json/form content-types
    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct or "application/x-www-form-urlencoded" in ct:
        raise HTTPException(
            status_code=415,
            detail="Unsupported Media Type for plain text endpoint",
        )
    raw = await request.body()
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid text body encoding")
    m = re.search(r"city\s*:\s*([^\s,]+)", text, flags=re.IGNORECASE)
    if not m:
        raise HTTPException(
            status_code=422, detail="Plain text must contain pattern 'city: <value>'"
        )
    return m.group(1).strip()


@app.post("/weather/forecast_nested_json")
async def weather_forecast_nested_json(request: Request) -> Any:
    city = await _extract_city_json_nested(request)
    return {"weather": f"sunny in {city}"}


@app.post("/weather/forecast_top_json")
async def weather_forecast_top_json(request: Request) -> Any:
    city = await _extract_city_json_top_level(request)
    return {"weather": f"sunny in {city}"}


@app.post("/array/process_json")
async def process_array_json(request: Request) -> Any:
    city = await _extract_city_json_array(request)
    return {"processed_city": city}


@app.post("/raw/echo_text")
async def echo_raw_text(request: Request) -> Any:
    city = await _extract_city_plain_text(request)
    return {"city": city}


@app.post("/weather/forecast_form")
async def weather_forecast_form(request: Request) -> Any:
    city = await _extract_city_form(request)
    return {"weather": f"sunny in {city}"}


@app.api_route("/findWeather", methods=["GET", "POST"])
async def find_weather(request: Request, city: Optional[str] = Query(None)) -> Any:
    if city is None:
        data = await request.json()
        city = data.get("city", "")

    city_norm = city.strip()
    if city_norm == "Casablanca":
        return {"weather": {"temperature": 22, "weather": "Sunny"}}
    elif city_norm == "Zurich":
        return {"weather": {"temperature": 15, "weather": "Rainy"}}
    else:
        return {"weather": {"temperature": 0, "weather": "CITY NOT FOUND"}}


@app.api_route("/findUniversity", methods=["GET", "POST"])
async def find_university(request: Request, country: Optional[str] = Query(None)) -> Any:
    if country is None:
        data = await request.json()
        country = data.get("country", "")

    country_norm = country.strip()
    if country_norm == "Morocco":
        return {"university": "UM6P", "city": "Ben Guerir"}
    elif country_norm == "Switzerland":
        return {"university": "ETH Zurich", "city": "Zurich"}
    else:
        return {"university": "UNIVERSITY NOT FOUND", "city": "CITY NOT FOUND"}


@app.api_route("/findCity", methods=["GET", "POST"])
async def find_city(request: Request, country: Optional[str] = Query(None)) -> Any:
    if country is None:
        data = await request.json()
        country = data.get("country", "")

    country_norm = country.strip()
    if country_norm == "Morocco":
        return {"city": "Casablanca"}
    elif country_norm == "Switzerland":
        return {"city": "Zurich"}
    else:
        return {"city": "COUNTRY NOT FOUND"}


@app.post("/orders/{order_id}")
async def retrieve_product_with_id(
    order_id: str,
    request: Request,
    store_id: Optional[str] = Query(None),
    session_id: Optional[str] = Header(None),
) -> Any:
    data = await request.json()
    item_id = str(data.get("item_id", ""))

    if item_id == "1":
        product_name = "Airplane"
    else:
        product_name = "Car"

    return {
        "product": {
            "product_name": product_name,
            "product_id": item_id,
            "product_order_id": order_id,
            "product_store_id": store_id,
            "product_session_id": session_id,
        }
    }
