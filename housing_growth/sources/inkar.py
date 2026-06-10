import csv
import io
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


DEFAULT_INDICATORS = {
    "m_mietpr": ("asking_rent_eur_per_m2", "EUR_per_m2"),
    "d_KW_BL": ("building_land_price_eur_per_m2", "EUR_per_m2"),
    "xbev": ("population", "people"),
    "q_gen_wo_ew": ("building_permits_per_1000_residents", "per_1000_residents"),
    "q_fert_wo_bev": ("completed_new_apartments_per_1000_residents", "per_1000_residents"),
    "q_wofl_bev": ("living_space_m2_per_resident", "m2_per_resident"),
}


@dataclass(frozen=True)
class InkarExtractResult:
    rows_written: int
    cities_included: int
    indicators_included: int


def extract_inkar_city_observations(
    archive_path: str,
    reference_xlsx_path: str,
    output_path: str,
    indicators: Optional[Sequence[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    raumbezug: str = "Kreise",
    bereich: str = "LRB",
    city_type: str = "Kreisfreie Stadt",
) -> InkarExtractResult:
    """Extract selected real INKAR observations for independent German cities.

    INKAR's 2025 zip uses a compression method unsupported by Python 3.9's
    zipfile reader for the huge CSV, so the CSV stream is provided by the
    system unzip command and parsed with Python's csv module.
    """
    selected = {
        code: DEFAULT_INDICATORS[code]
        for code in (indicators or tuple(DEFAULT_INDICATORS))
        if code in DEFAULT_INDICATORS
    }
    unknown = sorted(set(indicators or []) - set(DEFAULT_INDICATORS))
    if unknown:
        raise ValueError(f"Unsupported INKAR indicator code(s): {', '.join(unknown)}")

    city_names = read_kreis_city_names(reference_xlsx_path, city_type=city_type)
    rows = []
    archive = Path(archive_path)
    if not archive.exists():
        raise FileNotFoundError(f"INKAR archive not found: {archive}")

    process = subprocess.Popen(
        ["unzip", "-p", str(archive), "inkar_2025.csv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise RuntimeError("Could not open unzip output stream.")

    try:
        stream = io.TextIOWrapper(process.stdout, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(stream, delimiter=";")
        for raw in reader:
            if raw.get("Bereich") != bereich:
                continue
            if raw.get("Raumbezug") != raumbezug:
                continue

            code = raw.get("Kuerzel", "")
            if code not in selected:
                continue

            city_id = normalize_kennziffer(raw.get("Kennziffer", ""))
            if city_id not in city_names:
                continue

            year = int(raw["Zeitbezug"])
            if start_year is not None and year < start_year:
                continue
            if end_year is not None and year > end_year:
                continue

            value = parse_inkar_number(raw.get("Wert", ""))
            if value is None:
                continue

            metric, unit = selected[code]
            rows.append(
                {
                    "city": city_names[city_id],
                    "city_id": city_id,
                    "year": str(year),
                    "metric": metric,
                    "value": f"{value:.6f}".rstrip("0").rstrip("."),
                    "unit": unit,
                    "source": f"BBSR INKAR 2025 {code}",
                }
            )
    finally:
        if process.stdout is not None:
            process.stdout.close()

    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"unzip failed with exit code {return_code}: {stderr.strip()}")

    rows.sort(key=lambda item: (item["metric"], item["city"], int(item["year"])))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["city", "city_id", "year", "metric", "value", "unit", "source"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return InkarExtractResult(
        rows_written=len(rows),
        cities_included=len({row["city_id"] for row in rows}),
        indicators_included=len({row["metric"] for row in rows}),
    )


def read_kreis_city_names(reference_xlsx_path: str, city_type: str = "Kreisfreie Stadt") -> Dict[str, str]:
    rows = read_xlsx_sheet_rows(reference_xlsx_path, "Kreisreferenz")
    if len(rows) < 3:
        raise ValueError("Kreisreferenz sheet does not contain data rows.")

    headers = rows[0]
    id_index = headers.index("KRS2023")
    name_index = headers.index("KRS_NAME")
    type_index = headers.index("SLK_NAME")

    city_names: Dict[str, str] = {}
    for row in rows[2:]:
        if len(row) <= max(id_index, name_index, type_index):
            continue
        if row[type_index] != city_type:
            continue
        city_names[normalize_kennziffer(row[id_index])] = row[name_index]
    return city_names


def read_xlsx_sheet_rows(path: str, sheet_name: str) -> List[List[str]]:
    with zipfile.ZipFile(path) as workbook:
        ns = {
            "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        strings = _shared_strings(workbook, ns)
        workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
        relationships = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        relationship_map = {
            relationship.attrib["Id"]: relationship.attrib["Target"]
            for relationship in relationships
        }
        sheet_relationship_id = None
        relationship_attr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        for sheet in workbook_xml.findall(".//a:sheet", ns):
            if sheet.attrib.get("name") == sheet_name:
                sheet_relationship_id = sheet.attrib[relationship_attr]
                break
        if sheet_relationship_id is None:
            raise ValueError(f"Sheet not found in workbook: {sheet_name}")

        sheet_path = "xl/" + relationship_map[sheet_relationship_id].lstrip("/")
        sheet_xml = ET.fromstring(workbook.read(sheet_path))
        rows = []
        for row in sheet_xml.findall(".//a:row", ns):
            cells: Dict[int, str] = {}
            for cell in row.findall("a:c", ns):
                ref = cell.attrib.get("r", "")
                column = _column_index(ref)
                cells[column] = _cell_text(cell, strings, ns)
            if cells:
                rows.append([cells.get(index, "") for index in range(max(cells) + 1)])
        return rows


def parse_inkar_number(raw: str) -> Optional[float]:
    value = raw.strip()
    if value in {"", "NA", "NaN"}:
        return None
    return float(value.replace(".", "").replace(",", "."))


def normalize_kennziffer(value: str) -> str:
    return value.strip().zfill(8)


def _shared_strings(workbook: zipfile.ZipFile, ns: Dict[str, str]) -> List[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    return [
        "".join(text.text or "" for text in item.findall(".//a:t", ns))
        for item in root.findall("a:si", ns)
    ]


def _cell_text(cell: ET.Element, strings: Sequence[str], ns: Dict[str, str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", ns))
    value = cell.find("a:v", ns)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        return strings[int(value.text)]
    return value.text


def _column_index(cell_reference: str) -> int:
    column_letters = "".join(ch for ch in cell_reference if ch.isalpha())
    index = 0
    for char in column_letters:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index - 1
