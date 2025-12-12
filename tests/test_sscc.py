"""
SSCC Generator Tests
====================
Tests for GS1 SSCC-18 generation and validation.

Author: Integration Engineering Team
"""

import pytest
from src.sscc.generator import SSCCGenerator, create_sscc_generator
from src.models.label_models import SSCCConfig, SSCC


class TestSSCCCheckDigitCalculation:
    """Test GS1 check digit calculation algorithm."""

    def test_check_digit_calculation_example_1(self):
        """Test check digit for SSCC example."""
        # Example from GS1 documentation
        # SSCC: 0 0614141 123456789 0
        check_digit = SSCCGenerator._calculate_check_digit(
            extension="0",
            company_prefix="0614141",
            serial_reference="123456789"
        )
        assert check_digit == "0"

    def test_check_digit_calculation_example_2(self):
        """Test another check digit calculation."""
        # SSCC: 0 0614141 000000001 2
        check_digit = SSCCGenerator._calculate_check_digit(
            extension="0",
            company_prefix="0614141",
            serial_reference="000000001"
        )
        assert check_digit == "2"

    def test_check_digit_all_zeros(self):
        """Test check digit when all digits are zeros."""
        check_digit = SSCCGenerator._calculate_check_digit(
            extension="0",
            company_prefix="0000000",
            serial_reference="000000000"
        )
        # All zeros should result in check digit 0
        assert check_digit == "0"

    def test_check_digit_all_nines(self):
        """Test check digit with all nines."""
        check_digit = SSCCGenerator._calculate_check_digit(
            extension="9",
            company_prefix="9999999",
            serial_reference="999999999"
        )
        # Should be valid digit
        assert check_digit in "0123456789"


class TestSSCCGenerator:
    """Test SSCC generator functionality."""

    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        config = SSCCConfig(
            company_prefix="0614141",
            extension_digit="0",
            serial_start=1
        )
        generator = SSCCGenerator(config)
        assert generator.current_serial == 1
        assert generator.config.company_prefix == "0614141"

    def test_generate_single_sscc(self):
        """Test generating a single SSCC."""
        generator = create_sscc_generator(company_prefix="0614141")
        sscc = generator.generate_next()

        # Verify structure
        assert sscc.extension_digit == "0"
        assert sscc.company_prefix == "0614141"
        assert len(sscc.get_full_sscc()) == 18

        # Verify check digit is valid
        assert SSCCGenerator.validate_sscc(sscc)

    def test_generate_sequential_ssccs(self):
        """Test generating multiple SSCCs in sequence."""
        generator = create_sscc_generator(
            company_prefix="0614141",
            serial_start=1,
            serial_padding=9
        )

        sscc1 = generator.generate_next()
        sscc2 = generator.generate_next()
        sscc3 = generator.generate_next()

        # Verify serials are sequential
        assert sscc1.serial_reference == "000000001"
        assert sscc2.serial_reference == "000000002"
        assert sscc3.serial_reference == "000000003"

        # All should have valid check digits
        assert SSCCGenerator.validate_sscc(sscc1)
        assert SSCCGenerator.validate_sscc(sscc2)
        assert SSCCGenerator.validate_sscc(sscc3)

    def test_generate_batch(self):
        """Test batch generation."""
        generator = create_sscc_generator(company_prefix="0614141")
        batch = generator.generate_batch(10)

        assert len(batch) == 10

        # Verify all are unique
        sscc_strings = [sscc.get_full_sscc() for sscc in batch]
        assert len(set(sscc_strings)) == 10

        # Verify all are valid
        for sscc in batch:
            assert SSCCGenerator.validate_sscc(sscc)

    def test_reset_generator(self):
        """Test resetting the serial counter."""
        generator = create_sscc_generator(serial_start=1)

        # Generate some SSCCs
        generator.generate_next()
        generator.generate_next()
        assert generator.current_serial == 3

        # Reset
        generator.reset()
        assert generator.current_serial == 1

        # Reset to specific value
        generator.reset(start_serial=100)
        assert generator.current_serial == 100

    def test_peek_next_sscc(self):
        """Test peeking at next SSCC without generating."""
        generator = create_sscc_generator(serial_start=1)

        next_sscc = generator.peek_next_sscc()
        assert len(next_sscc) == 18

        # Verify peek doesn't increment
        assert generator.current_serial == 1

        # Generate and verify it matches peek
        generated = generator.generate_next()
        assert generated.get_full_sscc() == next_sscc

    def test_serial_padding(self):
        """Test serial number padding."""
        generator = create_sscc_generator(
            company_prefix="0614141",
            serial_start=5,
            serial_padding=9
        )

        sscc = generator.generate_next()
        assert sscc.serial_reference == "000000005"
        assert len(sscc.serial_reference) == 9

    def test_different_extension_digits(self):
        """Test SSCCs with different extension digits."""
        for ext in range(10):
            generator = create_sscc_generator(
                company_prefix="0614141",
                extension_digit=str(ext),
                serial_start=1
            )
            sscc = generator.generate_next()
            assert sscc.extension_digit == str(ext)
            assert SSCCGenerator.validate_sscc(sscc)


class TestSSCCValidation:
    """Test SSCC validation logic."""

    def test_validate_correct_sscc(self):
        """Test validation of correct SSCC."""
        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="0"
        )
        assert SSCCGenerator.validate_sscc(sscc) is True

    def test_validate_incorrect_check_digit(self):
        """Test validation catches incorrect check digit."""
        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="7"  # Wrong! Should be 8
        )
        assert SSCCGenerator.validate_sscc(sscc) is False

    def test_validate_generated_sscc(self):
        """Test all generated SSCCs are valid."""
        generator = create_sscc_generator(company_prefix="0614141")

        for _ in range(20):
            sscc = generator.generate_next()
            assert SSCCGenerator.validate_sscc(sscc)


class TestSSCCFormatting:
    """Test SSCC formatting methods."""

    def test_get_full_sscc(self):
        """Test getting full 18-digit SSCC."""
        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="8"
        )
        full_sscc = sscc.get_full_sscc()
        assert full_sscc == "006141411234567898"
        assert len(full_sscc) == 18

    def test_get_formatted_sscc(self):
        """Test formatted SSCC with separators."""
        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="8"
        )
        formatted = sscc.get_formatted_sscc(separator=" ")
        assert "0614141" in formatted
        assert "123456789" in formatted

    def test_get_gs1_application_identifier(self):
        """Test GS1 AI format."""
        sscc = SSCC(
            extension_digit="0",
            company_prefix="0614141",
            serial_reference="123456789",
            check_digit="8"
        )
        ai_format = sscc.get_gs1_application_identifier()
        assert ai_format.startswith("(00)")
        assert "006141411234567898" in ai_format


class TestSSCCEdgeCases:
    """Test edge cases and error conditions."""

    def test_max_serial_number(self):
        """Test behavior near maximum serial number."""
        generator = create_sscc_generator(
            company_prefix="0614141",
            serial_start=999999998,
            serial_padding=9
        )

        sscc1 = generator.generate_next()
        assert sscc1.serial_reference == "999999998"

        sscc2 = generator.generate_next()
        assert sscc2.serial_reference == "999999999"

    def test_serial_overflow(self):
        """Test behavior when serial exceeds padding."""
        generator = create_sscc_generator(
            company_prefix="0614141",
            serial_start=999999999,
            serial_padding=9
        )

        # Generate one within limit
        generator.generate_next()

        # Next should exceed padding
        with pytest.raises(ValueError, match="exceeds maximum padding"):
            generator.generate_next()

    def test_different_company_prefix_lengths(self):
        """Test with various company prefix lengths (7-10 digits)."""
        prefixes = [
            "0614141",      # 7 digits (standard)
            "06141410",     # 8 digits
            "061414100",    # 9 digits
            "0614141000"    # 10 digits
        ]

        for prefix in prefixes:
            generator = create_sscc_generator(company_prefix=prefix)
            sscc = generator.generate_next()
            assert sscc.company_prefix == prefix
            assert SSCCGenerator.validate_sscc(sscc)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
