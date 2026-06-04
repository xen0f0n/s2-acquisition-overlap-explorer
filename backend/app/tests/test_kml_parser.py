from pathlib import Path

from app.ingest.kml_parser import parse_kml_file
from app.ingest.scrape import DownloadedPlan


def test_parse_simple_kml(tmp_path: Path):
    kml = tmp_path / "sample.kml"
    kml.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <Placemark>
    <name>S2A Nominal 20260604T100000 20260604T100500</name>
    <TimeSpan><begin>2026-06-04T10:00:00Z</begin><end>2026-06-04T10:05:00Z</end></TimeSpan>
    <ExtendedData><Data name="orbit"><value>123</value></Data></ExtendedData>
    <Polygon><outerBoundaryIs><LinearRing><coordinates>
      20,35,0 21,35,0 21,36,0 20,36,0 20,35,0
    </coordinates></LinearRing></outerBoundaryIs></Polygon>
  </Placemark>
</Document>
</kml>"""
    )
    plan = DownloadedPlan(
        platform="S2A",
        label="demo",
        url="demo",
        filename="sample.kml",
        plan_start_utc="2026-06-04T00:00:00Z",
        plan_stop_utc="2026-06-05T00:00:00Z",
        downloaded_at_utc="2026-06-04T00:00:00Z",
        sha256="abc1234567890",
        local_path=str(kml),
    )
    gdf = parse_kml_file(plan)
    assert len(gdf) == 1
    assert gdf.iloc[0]["platform"] == "S2A"
    assert gdf.iloc[0]["mode"] == "Nominal"
    assert gdf.iloc[0]["geometry"].is_valid
