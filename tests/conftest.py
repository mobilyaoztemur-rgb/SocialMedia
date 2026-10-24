from copy import deepcopy
from pathlib import Path
import pytest
from woodmood.db import Store
from woodmood.settings import load_settings
from woodmood.source import parse_project

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cfg(tmp_path):
    cfg = deepcopy(load_settings())
    cfg["data_dir"] = tmp_path
    return cfg


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.sqlite3")


@pytest.fixture
def project(cfg):
    return parse_project((FIXTURES / "project.html").read_text(),
                         "https://woodmoodmobilya.com/tr/projeler/ornek-a", cfg["source"])
