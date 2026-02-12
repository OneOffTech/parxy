from unittest.mock import patch

from parxy_core.exceptions import (
    AuthenticationException,
    FileNotFoundException,
    ParsingException,
    QuotaExceededException,
    RateLimitException,
)
from parxy_core.facade.circuit_breaker import CircuitBreakerState
from parxy_core.facade import Parxy
from parxy_core.models import Document, Page


class TestCircuitBreakerState:
    def test_circuit_initially_closed(self):
        breaker = CircuitBreakerState()

        assert breaker.is_open('llamaparse') is False
        assert breaker.get_trip_exception('llamaparse') is None

    def test_authentication_exception_trips_circuit(self):
        breaker = CircuitBreakerState()
        exc = AuthenticationException('Invalid API key', service='llamaparse')

        breaker.record_failure('llamaparse', exc)

        assert breaker.is_open('llamaparse') is True
        assert breaker.get_trip_exception('llamaparse') is exc

    def test_quota_exceeded_exception_trips_circuit(self):
        breaker = CircuitBreakerState()
        exc = QuotaExceededException('Quota exhausted', service='llamaparse')

        breaker.record_failure('llamaparse', exc)

        assert breaker.is_open('llamaparse') is True
        assert breaker.get_trip_exception('llamaparse') is exc

    def test_rate_limit_exception_trips_circuit(self):
        breaker = CircuitBreakerState()
        exc = RateLimitException('Rate limit exceeded', service='llamaparse')

        breaker.record_failure('llamaparse', exc)

        assert breaker.is_open('llamaparse') is True
        assert breaker.get_trip_exception('llamaparse') is exc

    def test_file_not_found_does_not_trip(self):
        breaker = CircuitBreakerState()
        exc = FileNotFoundException('File missing', service='llamaparse')

        breaker.record_failure('llamaparse', exc)

        assert breaker.is_open('llamaparse') is False

    def test_parsing_exception_does_not_trip(self):
        breaker = CircuitBreakerState()
        exc = ParsingException('Parse error', service='llamaparse')

        breaker.record_failure('llamaparse', exc)

        assert breaker.is_open('llamaparse') is False

    def test_generic_exception_does_not_trip(self):
        breaker = CircuitBreakerState()
        exc = Exception('Something went wrong')

        breaker.record_failure('llamaparse', exc)

        assert breaker.is_open('llamaparse') is False

    def test_trip_is_per_driver(self):
        breaker = CircuitBreakerState()
        exc = AuthenticationException('Invalid API key', service='llamaparse')

        breaker.record_failure('llamaparse', exc)

        assert breaker.is_open('llamaparse') is True
        assert breaker.is_open('pdfact') is False

    def test_original_exception_preserved(self):
        breaker = CircuitBreakerState()
        exc = AuthenticationException('Invalid API key', service='llamaparse')

        breaker.record_failure('llamaparse', exc)

        retrieved = breaker.get_trip_exception('llamaparse')
        assert retrieved is exc
        assert isinstance(retrieved, AuthenticationException)

    def test_first_trip_exception_preserved(self):
        breaker = CircuitBreakerState()
        first = AuthenticationException('First error', service='llamaparse')
        second = RateLimitException('Second error', service='llamaparse')

        breaker.record_failure('llamaparse', first)
        breaker.record_failure('llamaparse', second)

        assert breaker.get_trip_exception('llamaparse') is first


class TestBatchCircuitBreaker:
    @patch.object(Parxy, 'parse')
    def test_auth_failure_short_circuits_remaining_tasks(self, mock_parse):
        exc = AuthenticationException('Invalid API key', service='pymupdf')
        mock_parse.side_effect = exc

        results = Parxy.batch(
            tasks=['doc1.pdf', 'doc2.pdf', 'doc3.pdf'],
            workers=1,
        )

        assert len(results) == 3
        assert all(r.failed for r in results)
        # Only the first call should actually reach parse
        assert mock_parse.call_count == 1
        # All results carry the tripping exception
        for r in results:
            assert r.exception is exc

    @patch.object(Parxy, 'parse')
    def test_quota_failure_short_circuits_remaining_tasks(self, mock_parse):
        exc = QuotaExceededException('Quota exhausted', service='pymupdf')
        mock_parse.side_effect = exc

        results = Parxy.batch(
            tasks=['doc1.pdf', 'doc2.pdf'],
            workers=1,
        )

        assert len(results) == 2
        assert mock_parse.call_count == 1
        assert all(r.exception is exc for r in results)

    @patch.object(Parxy, 'parse')
    def test_rate_limit_failure_short_circuits_remaining_tasks(self, mock_parse):
        exc = RateLimitException('Rate limit exceeded', service='pymupdf')
        mock_parse.side_effect = exc

        results = Parxy.batch(
            tasks=['doc1.pdf', 'doc2.pdf'],
            workers=1,
        )

        assert len(results) == 2
        assert mock_parse.call_count == 1
        assert all(r.exception is exc for r in results)

    @patch.object(Parxy, 'parse')
    def test_file_not_found_does_not_short_circuit(self, mock_parse):
        call_count = 0

        def parse_side_effect(file, level, driver_name):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundException('File missing', service='pymupdf')
            return Document(pages=[Page(number=1, text='test')])

        mock_parse.side_effect = parse_side_effect

        results = Parxy.batch(
            tasks=['missing.pdf', 'doc2.pdf', 'doc3.pdf'],
            workers=1,
        )

        assert len(results) == 3
        assert mock_parse.call_count == 3
        assert sum(1 for r in results if r.failed) == 1
        assert sum(1 for r in results if r.success) == 2

    @patch.object(Parxy, 'parse')
    def test_per_driver_isolation(self, mock_parse):
        auth_exc = AuthenticationException('Invalid API key', service='llamaparse')

        def parse_side_effect(file, level, driver_name):
            if driver_name == 'llamaparse':
                raise auth_exc
            return Document(pages=[Page(number=1, text='test')])

        mock_parse.side_effect = parse_side_effect

        results = Parxy.batch(
            tasks=['doc1.pdf', 'doc2.pdf'],
            drivers=['llamaparse', 'pymupdf'],
            workers=1,
        )

        # 2 files x 2 drivers = 4 results
        assert len(results) == 4

        llama_results = [r for r in results if r.driver == 'llamaparse']
        pymupdf_results = [r for r in results if r.driver == 'pymupdf']

        # All llamaparse results should fail
        assert all(r.failed for r in llama_results)
        # Only 1 actual parse call for llamaparse (second is short-circuited)
        assert all(r.exception is auth_exc for r in llama_results)

        # All pymupdf results should succeed
        assert all(r.success for r in pymupdf_results)

    @patch.object(Parxy, 'parse')
    def test_short_circuited_result_has_correct_fields(self, mock_parse):
        exc = AuthenticationException('Bad key', service='llamaparse')
        mock_parse.side_effect = exc

        results = Parxy.batch(
            tasks=['doc1.pdf', 'doc2.pdf'],
            drivers=['llamaparse'],
            workers=1,
        )

        # Second result is the short-circuited one
        short_circuited = results[1]
        assert short_circuited.file == 'doc2.pdf'
        assert short_circuited.driver == 'llamaparse'
        assert short_circuited.document is None
        assert short_circuited.error == str(exc)
        assert short_circuited.exception is exc
        assert short_circuited.failed is True
        assert short_circuited.success is False
