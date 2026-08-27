def test_storage_configuration_defaults():
    from app.core.config import STORAGE_BACKEND, STORAGE_PATH

    assert STORAGE_BACKEND == "local"
    assert STORAGE_PATH == "./evidence-data"