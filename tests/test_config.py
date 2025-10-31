from pydantic import SecretStr
import pytest

from parxy_core.models.config import LlmWhispererConfig, LlamaParseConfig, PdfActConfig


class TestConfig:
    @pytest.mark.parametrize(
        'config_class', [LlmWhispererConfig, LlamaParseConfig, PdfActConfig]
    )
    def test_sensitive_field_hidden_when_dumping_config(self, config_class):
        """Test that api_key is properly masked in all configuration classes that use it."""
        config = config_class(api_key='test')
        json_output = config.model_dump_json()
        dictionary_output = config.model_dump()

        assert '**********' == str(config.api_key)
        assert isinstance(config.api_key, SecretStr)
        assert '"api_key"' not in json_output
        assert 'api_key' not in dictionary_output
