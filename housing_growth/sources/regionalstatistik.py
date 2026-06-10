from typing import Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://www.regionalstatistik.de/genesisws/rest/2020/data/table"


def build_table_payload(
    table: str,
    username: str,
    password: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    language: str = "en",
) -> Dict[str, str]:
    payload = {
        "username": username,
        "password": password,
        "name": table,
        "area": "all",
        "compress": "false",
        "transpose": "false",
        "format": "csv",
        "language": language,
    }
    if start_year is not None:
        payload["startyear"] = str(start_year)
    if end_year is not None:
        payload["endyear"] = str(end_year)
    return payload


def fetch_table_csv(
    table: str,
    username: str,
    password: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    timeout: int = 60,
) -> str:
    """Fetch a raw CSV table from the Regionalstatistik GENESIS REST API.

    The API requires free registration. The raw GENESIS table still needs to be
    normalized into the city/year/metric/value CSV contract before analysis.
    """
    payload = build_table_payload(
        table=table,
        username=username,
        password=password,
        start_year=start_year,
        end_year=end_year,
    )
    request = Request(
        BASE_URL,
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")
