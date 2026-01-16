# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/weather/{city}")
async def root(city):
    if city.lower() == "agadir":
        return {"weather": "sunny"}
    elif city.lower() == "paris":
        return {"weather": "cloudy"}
    else:
        return {"weather": "windy"}
