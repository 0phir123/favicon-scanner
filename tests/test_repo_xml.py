# /tests/test_repo_xml.py
from __future__ import annotations
from pathlib import Path
import tempfile
from app.adapters.repositories.rapid7_xml_repo import Rapid7XMLRepository

def test_repo_parses_and_looks_up() -> None:
    xml = """
    <favicons>
      <favicon>
        <md5>aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</md5>
        <name>Foo</name>
        <properties><property name="vendor">Acme</property></properties>
      </favicon>
    </favicons>
    """
    p = Path(tempfile.gettempdir()) / "fav_test.xml"
    p.write_text(xml, encoding="utf-8")
    repo = Rapid7XMLRepository(str(p))
    out = repo.lookup_md5("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert len(out) == 1 and out[0]["name"] == "Foo"
    