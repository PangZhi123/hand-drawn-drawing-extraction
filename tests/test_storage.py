import pytest

from app.core.errors import DrawingError
from app.services.storage import FileStorage


def test_result_id_rejects_path_traversal(tmp_path):
    storage = FileStorage(tmp_path)
    with pytest.raises(DrawingError) as error:
        storage.result_path("../../secret")
    assert error.value.code == "DE0401"
