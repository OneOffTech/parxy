"""Tests for middleware base classes and pipeline integration."""

from parxy_core.models import Document, ParsingRequest, Page
from parxy_core.models.config import ParxyConfig
from parxy_core.middleware import Middleware, SimpleMiddleware
from parxy_core.facade import Parxy
from parxy_core.drivers import Driver


class TestMiddlewareBase:
    """Test middleware base class functionality."""

    def test_middleware_with_only_handle(self):
        """Test middleware with only handle() method."""

        class TestHandleMiddleware(SimpleMiddleware):
            def handle(self, request: ParsingRequest, next) -> Document:
                request.config['test_flag'] = True
                return next(request)

        middleware = TestHandleMiddleware()
        assert hasattr(middleware, 'handle')
        assert hasattr(middleware, 'terminate')

    def test_middleware_with_only_terminate(self):
        """Test middleware with only terminate() method."""

        class TestTerminateMiddleware(SimpleMiddleware):
            def terminate(self, document: Document, next) -> Document:
                document.parsing_metadata = document.parsing_metadata or {}
                document.parsing_metadata['test'] = 'processed'
                return next(document)

        middleware = TestTerminateMiddleware()
        assert hasattr(middleware, 'handle')
        assert hasattr(middleware, 'terminate')

    def test_middleware_with_both(self):
        """Test middleware with both handle() and terminate() methods."""

        class TestBothMiddleware(Middleware):
            def handle(self, request: ParsingRequest, next) -> Document:
                request.config['handle_called'] = True
                return next(request)

            def terminate(self, document: Document, next) -> Document:
                document.parsing_metadata = document.parsing_metadata or {}
                document.parsing_metadata['terminate_called'] = True
                return next(document)

        middleware = TestBothMiddleware()
        assert hasattr(middleware, 'handle')
        assert hasattr(middleware, 'terminate')


class TestMiddlewareRegistry:
    """Test Parxy-level middleware registration."""

    def test_global_middleware_registry_configuration(self):
        """Test that global middleware can be registered and cleared."""
        Parxy.clear_middleware()

        class TestMiddleware(Middleware):
            def handle(self, request: ParsingRequest, next) -> Document:
                return next(request)

        Parxy.with_middleware([TestMiddleware()])

        assert len(Parxy.get_middleware()) == 1

        Parxy.clear_middleware()

    def test_execution_order(self):
        """Test that middleware are stored in registration order."""
        Parxy.clear_middleware()

        class LoggingMiddleware(Middleware):
            def __init__(self, name: str):
                self.name = name

            def handle(self, request: ParsingRequest, next) -> Document:
                return next(request)

        Parxy.with_middleware(
            [LoggingMiddleware('A'), LoggingMiddleware('B'), LoggingMiddleware('C')]
        )

        middleware_list = Parxy.get_middleware()
        assert len(middleware_list) == 3
        assert middleware_list[0].name == 'A'
        assert middleware_list[1].name == 'B'
        assert middleware_list[2].name == 'C'

        Parxy.clear_middleware()

    def test_string_loading(self):
        """Test loading middleware from a dotted string path."""
        Parxy.clear_middleware()

        Parxy.with_middleware(['parxy_core.middleware.SimpleMiddleware'])

        middleware_list = Parxy.get_middleware()
        assert len(middleware_list) == 1
        assert isinstance(middleware_list[0], SimpleMiddleware)

        Parxy.clear_middleware()

    def test_driver_middleware_persists_on_singleton(self):
        """Test that driver middleware persists across singleton lookups."""
        driver = Parxy.driver('pymupdf')

        class TestDriverMiddleware(Middleware):
            def handle(self, request: ParsingRequest, next) -> Document:
                return next(request)

        driver.with_middleware(TestDriverMiddleware())
        assert len(driver.get_middleware()) == 1

        driver2 = Parxy.driver('pymupdf')
        assert len(driver2.get_middleware()) == 1

        driver.clear_middleware()
        assert len(driver.get_middleware()) == 0


class TestMiddlewarePipelineOrder:
    """Test runtime handle/terminate execution order."""

    def test_driver_parse_executes_middleware_chain_in_expected_order(self):
        """Global handle → driver handle → driver terminate → global terminate."""
        execution_log = []

        class RecordingMiddleware(Middleware):
            def __init__(self, name: str):
                self.name = name

            def handle(self, request: ParsingRequest, next) -> Document:
                execution_log.append(f'{self.name}.handle')
                request.config[f'{self.name}_seen'] = True
                return next(request)

            def terminate(self, document: Document, next) -> Document:
                execution_log.append(f'{self.name}.terminate')
                return next(document)

        class DummyDriver(Driver):
            supported_levels = ['block']

            def _handle(self, file, level='block', **kwargs) -> Document:
                assert kwargs.get('global_seen') is True
                assert kwargs.get('driver_seen') is True
                return Document(pages=[Page(number=1, text='ok', blocks=[])])

        Parxy.clear_middleware()
        Parxy.with_middleware([RecordingMiddleware('global')])

        driver = DummyDriver(config={})
        driver.with_middleware(RecordingMiddleware('driver'))

        driver.parse(file=b'dummy-bytes', level='block')

        assert execution_log == [
            'global.handle',
            'driver.handle',
            'driver.terminate',
            'global.terminate',
        ]

        driver.clear_middleware()
        Parxy.clear_middleware()


class TestMiddlewareConfig:
    """Test ParxyConfig middleware field."""

    def test_config_stores_middleware_class_paths(self):
        """Test that ParxyConfig accepts and stores middleware string paths."""
        config = ParxyConfig(middleware=['parxy_core.middleware.SimpleMiddleware'])

        assert config.middleware is not None
        assert len(config.middleware) == 1
        assert config.middleware[0] == 'parxy_core.middleware.SimpleMiddleware'

    def test_config_middleware_defaults_to_none(self):
        """Test that middleware is None when not configured."""
        config = ParxyConfig()
        assert config.middleware is None

    def test_config_middleware_from_json_string(self):
        """Test that middleware accepts a JSON array string."""
        config = ParxyConfig(middleware='["parxy_core.middleware.SimpleMiddleware"]')
        assert config.middleware == ['parxy_core.middleware.SimpleMiddleware']

    def test_config_middleware_from_comma_separated_string(self):
        """Test that middleware accepts a comma-separated string."""
        config = ParxyConfig(
            middleware='parxy_core.middleware.SimpleMiddleware, parxy_core.middleware.SimpleMiddleware'
        )
        assert config.middleware == [
            'parxy_core.middleware.SimpleMiddleware',
            'parxy_core.middleware.SimpleMiddleware',
        ]

    def test_config_middleware_comma_separated_single_entry(self):
        """Test that a single comma-separated entry (no comma) is parsed correctly."""
        config = ParxyConfig(middleware='parxy_core.middleware.SimpleMiddleware')
        assert config.middleware == ['parxy_core.middleware.SimpleMiddleware']

    def test_config_middleware_survives_clear(self):
        """Config-layer middleware must not be removed by clear_middleware()."""
        from parxy_core.drivers import DriverFactory

        DriverFactory.reset()
        try:
            factory = DriverFactory.__new__(DriverFactory).initialize(
                ParxyConfig(middleware=['parxy_core.middleware.SimpleMiddleware'])
            )

            assert len(factory.get_middleware()) == 1

            factory.clear_middleware()

            # Config middleware is preserved; runtime layer was empty so count stays 1.
            assert len(factory.get_middleware()) == 1
            assert isinstance(factory.get_middleware()[0], SimpleMiddleware)
        finally:
            DriverFactory.reset()

    def test_runtime_middleware_cleared_config_middleware_preserved(self):
        """clear_middleware() removes runtime entries but keeps config entries."""
        from parxy_core.drivers import DriverFactory

        DriverFactory.reset()
        try:
            factory = DriverFactory.__new__(DriverFactory).initialize(
                ParxyConfig(middleware=['parxy_core.middleware.SimpleMiddleware'])
            )

            class ExtraMiddleware(Middleware):
                def handle(self, request, next):
                    return next(request)

            factory.with_middleware([ExtraMiddleware()])
            assert len(factory.get_middleware()) == 2

            factory.clear_middleware()

            remaining = factory.get_middleware()
            assert len(remaining) == 1
            assert isinstance(remaining[0], SimpleMiddleware)
        finally:
            DriverFactory.reset()
