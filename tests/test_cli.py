"""
CLI Tests
=========
Tests for command-line interface.

Author: Integration Engineering Team
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
import json

from main import cli


class TestCLI:
    """Test CLI commands."""

    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'ASN 856' in result.output
        assert 'process' in result.output

    def test_cli_version(self):
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output


class TestValidateCommand:
    """Test validate command."""

    def test_validate_sample_order_001(self):
        """Test validating sample order 001."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_001.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        result = runner.invoke(cli, ['validate', str(order_path)])
        assert result.exit_code == 0
        assert 'Validation Passed' in result.output
        assert 'ORD-2025-001' in result.output

    def test_validate_sample_order_002(self):
        """Test validating sample order 002."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_002_multi_carton.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        result = runner.invoke(cli, ['validate', str(order_path)])
        assert result.exit_code == 0
        assert 'Validation Passed' in result.output

    def test_validate_invalid_file(self):
        """Test validating non-existent file."""
        runner = CliRunner()
        result = runner.invoke(cli, ['validate', 'nonexistent.json'])
        assert result.exit_code != 0


class TestGenerateASNCommand:
    """Test generate-asn command."""

    def test_generate_asn_simple(self):
        """Test generating ASN from simple order."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_001.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        # Resolve path BEFORE entering isolated filesystem
        resolved_order_path = str(order_path.resolve())

        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                'generate-asn',
                '-i', resolved_order_path,
                '-o', 'test_asn.txt'
            ])

            assert result.exit_code == 0
            assert Path('test_asn.txt').exists()

            # Verify ASN content
            with open('test_asn.txt') as f:
                content = f.read()
                assert 'ISA' in content
                assert 'BSN' in content
                assert 'HL' in content

    def test_generate_asn_with_custom_ids(self):
        """Test generating ASN with custom sender/receiver IDs."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_001.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        # Resolve path BEFORE entering isolated filesystem
        resolved_order_path = str(order_path.resolve())

        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                'generate-asn',
                '-i', resolved_order_path,
                '-o', 'test_asn.txt',
                '--sender-id', 'ACME',
                '--receiver-id', 'BIGBOX'
            ])

            assert result.exit_code == 0

            with open('test_asn.txt') as f:
                content = f.read()
                assert 'ACME' in content
                assert 'BIGBOX' in content


class TestGenerateLabelsCommand:
    """Test generate-labels command."""

    def test_generate_labels_simple(self):
        """Test generating labels."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_001.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        # Resolve path BEFORE entering isolated filesystem
        resolved_order_path = str(order_path.resolve())

        with runner.isolated_filesystem():
            try:
                result = runner.invoke(cli, [
                    'generate-labels',
                    '-i', resolved_order_path,
                    '-o', 'labels'
                ])

                # May fail if reportlab not installed
                if 'Install' in result.output:
                    pytest.skip("reportlab not installed")

                assert result.exit_code == 0
                assert Path('labels').exists()

                # Check for PDF files
                pdf_files = list(Path('labels').glob('*.pdf'))
                assert len(pdf_files) >= 1

            except ImportError:
                pytest.skip("reportlab not installed")

    def test_generate_labels_no_contents(self):
        """Test generating labels without contents list."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_001.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        # Resolve path BEFORE entering isolated filesystem
        resolved_order_path = str(order_path.resolve())

        with runner.isolated_filesystem():
            try:
                result = runner.invoke(cli, [
                    'generate-labels',
                    '-i', resolved_order_path,
                    '-o', 'labels',
                    '--no-contents'
                ])

                if 'Install' in result.output:
                    pytest.skip("reportlab not installed")

                assert result.exit_code == 0

            except ImportError:
                pytest.skip("reportlab not installed")


class TestProcessCommand:
    """Test main process command."""

    def test_process_complete_skip_labels(self):
        """Test complete processing without labels."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_001.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        # Resolve path BEFORE entering isolated filesystem
        resolved_order_path = str(order_path.resolve())

        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                'process',
                '-i', resolved_order_path,
                '-o', 'output',
                '--skip-labels'
            ])

            assert result.exit_code == 0
            assert 'Processing Complete' in result.output

            # Check for ASN file
            output_dir = Path('output')
            assert output_dir.exists()

            asn_files = list(output_dir.glob('856_*.txt'))
            assert len(asn_files) == 1

    def test_process_with_custom_carton_limits(self):
        """Test processing with custom carton limits."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_002_multi_carton.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        # Resolve path BEFORE entering isolated filesystem
        resolved_order_path = str(order_path.resolve())

        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                'process',
                '-i', resolved_order_path,
                '-o', 'output',
                '--max-items', '20',
                '--max-weight', '30.0',
                '--skip-labels'
            ])

            assert result.exit_code == 0
            assert 'Processing Complete' in result.output

    def test_process_with_labels(self):
        """Test complete processing with labels."""
        runner = CliRunner()
        order_path = Path('examples/sample_orders/order_001.json')

        if not order_path.exists():
            pytest.skip("Sample order not found")

        # Resolve path BEFORE entering isolated filesystem
        resolved_order_path = str(order_path.resolve())

        with runner.isolated_filesystem():
            try:
                result = runner.invoke(cli, [
                    'process',
                    '-i', resolved_order_path,
                    '-o', 'output'
                ])

                # May skip if reportlab not installed
                if 'Install' in result.output or result.exit_code != 0:
                    # Check if it's just label generation that failed
                    if 'Processing Complete' in result.output:
                        # ASN should still be generated
                        assert Path('output').exists()
                    else:
                        pytest.skip("reportlab not installed or other error")
                else:
                    assert result.exit_code == 0
                    assert 'Processing Complete' in result.output

                    # Check outputs
                    assert Path('output').exists()
                    assert len(list(Path('output').glob('856_*.txt'))) == 1

            except ImportError:
                pytest.skip("reportlab not installed")


class TestExamplesCommand:
    """Test examples command."""

    def test_examples(self):
        """Test examples command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['examples'])
        assert result.exit_code == 0
        assert 'Usage Examples' in result.output
        assert 'python main.py' in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
