from pathlib import Path

import pytest

from langgraph_okf.agent.context import Context
from langgraph_okf.bundle import OKFBundle


@pytest.fixture
def context():
    return Context(bundle=OKFBundle(Path(__file__).parents[1] / "bundles/legal_sample"))
