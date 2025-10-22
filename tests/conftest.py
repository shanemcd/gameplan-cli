"""Shared fixtures for gameplan tests."""
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after the test."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample gameplan.yaml configuration."""
    return {
        "areas": {
            "jira": {
                "items": [
                    {"issue": "PROJ-123", "env": "prod"},
                    {"issue": "PROJ-456", "env": "stage"},
                ]
            }
        }
    }


@pytest.fixture
def config_file(temp_dir, sample_config):
    """Create a temporary gameplan.yaml file."""
    config_path = temp_dir / "gameplan.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config, f)
    return config_path


@pytest.fixture
def tracking_areas_structure(temp_dir):
    """Create tracking/areas directory structure."""
    tracking_dir = temp_dir / "tracking" / "areas"
    jira_area = tracking_dir / "jira"

    jira_area.mkdir(parents=True)
    (jira_area / "archive").mkdir()

    return {
        "root": temp_dir,
        "tracking": tracking_dir,
        "jira": jira_area,
    }
