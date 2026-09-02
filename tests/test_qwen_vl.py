from types import SimpleNamespace

from app.services.qwen_vl import _parse_message


def test_parse_message_reads_ollama_reasoning_field():
    message = SimpleNamespace(
        content="",
        reasoning='thinking... {"fixed_key_data":[{"field_name":"桩号"}]}',
    )

    data, _ = _parse_message(message)

    assert data["fixed_key_data"][0]["field_name"] == "桩号"


def test_parse_message_prefers_expected_schema_over_content_metadata():
    message = SimpleNamespace(
        content='{"status":"complete"}',
        reasoning_content='{"additional_observations":["识别到施工图"]}',
    )

    data, _ = _parse_message(message)

    assert data == {"additional_observations": ["识别到施工图"]}


def test_parse_message_unwraps_data_and_maps_chinese_keys():
    message = SimpleNamespace(
        content='{"data":{"固定关键数据":[{"field_name":"孔深","field_value":"10"}]}}',
    )

    data, _ = _parse_message(message)

    assert data["fixed_key_data"][0]["field_value"] == "10"


def test_parse_message_preserves_natural_language_for_fallback():
    message = SimpleNamespace(content="图中包含起止桩号和浇筑时间。")

    data, raw = _parse_message(message)

    assert data == {}
    assert "起止桩号" in raw
