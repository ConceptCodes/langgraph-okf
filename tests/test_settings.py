from langgraph_okf.settings import Settings


def test_settings_instantiates() -> None:
    assert isinstance(Settings(), Settings)
