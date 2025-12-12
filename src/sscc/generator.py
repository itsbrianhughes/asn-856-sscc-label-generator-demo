"""
SSCC Generator
==============
Generates GS1-compliant SSCC-18 (Serial Shipping Container Code) numbers.

The SSCC-18 structure:
- Extension Digit (1 digit): 0-9
- GS1 Company Prefix (7-10 digits): Assigned by GS1
- Serial Reference (variable length): Sequential number
- Check Digit (1 digit): Calculated using GS1 mod-10 algorithm

Total: 18 digits

Author: Integration Engineering Team
"""

from typing import Optional
import logging

from src.models.label_models import SSCC, SSCCConfig

logger = logging.getLogger(__name__)


class SSCCGenerator:
    """
    Generates GS1-compliant SSCC-18 serial numbers.

    Usage:
        config = SSCCConfig(company_prefix="0614141")
        generator = SSCCGenerator(config)
        sscc = generator.generate_next()
        print(sscc.get_full_sscc())  # 006141410000000018
    """

    def __init__(self, config: SSCCConfig):
        """
        Initialize the SSCC generator.

        Args:
            config: SSCC configuration with company prefix and starting serial
        """
        self.config = config
        self.current_serial = config.serial_start
        logger.info(
            f"SSCC Generator initialized with company prefix: {config.company_prefix}, "
            f"starting serial: {config.serial_start}"
        )

    def generate_next(self) -> SSCC:
        """
        Generate the next SSCC in the sequence.

        Returns:
            SSCC object with check digit calculated

        Raises:
            ValueError: If serial number exceeds available digits
        """
        serial_str = str(self.current_serial).zfill(self.config.serial_padding)

        # Validate serial doesn't exceed padding
        if len(serial_str) > self.config.serial_padding:
            raise ValueError(
                f"Serial number {self.current_serial} exceeds maximum padding "
                f"of {self.config.serial_padding} digits"
            )

        # Calculate check digit
        check_digit = self._calculate_check_digit(
            extension=self.config.extension_digit,
            company_prefix=self.config.company_prefix,
            serial_reference=serial_str
        )

        # Create SSCC object
        sscc = SSCC(
            extension_digit=self.config.extension_digit,
            company_prefix=self.config.company_prefix,
            serial_reference=serial_str,
            check_digit=check_digit
        )

        # Increment serial for next generation
        self.current_serial += 1

        logger.debug(f"Generated SSCC: {sscc.get_full_sscc()}")
        return sscc

    def generate_batch(self, count: int) -> list[SSCC]:
        """
        Generate a batch of SSCCs.

        Args:
            count: Number of SSCCs to generate

        Returns:
            List of SSCC objects
        """
        logger.info(f"Generating batch of {count} SSCCs")
        return [self.generate_next() for _ in range(count)]

    def reset(self, start_serial: Optional[int] = None):
        """
        Reset the serial counter.

        Args:
            start_serial: Optional new starting serial (defaults to config value)
        """
        if start_serial is not None:
            self.current_serial = start_serial
        else:
            self.current_serial = self.config.serial_start
        logger.info(f"SSCC Generator reset to serial: {self.current_serial}")

    @staticmethod
    def _calculate_check_digit(extension: str, company_prefix: str, serial_reference: str) -> str:
        """
        Calculate GS1 check digit using mod-10 algorithm.

        The GS1 mod-10 algorithm:
        1. Start from right to left (excluding check digit position)
        2. Multiply each digit alternately by 3 and 1
        3. Sum all products
        4. Subtract sum from nearest equal or higher multiple of 10
        5. Result is the check digit

        Args:
            extension: Extension digit (1 digit)
            company_prefix: GS1 company prefix (7-10 digits)
            serial_reference: Serial reference number

        Returns:
            Check digit as string (0-9)

        Example:
            Input: 0 0614141 123456789
            Calculation:
            Position:  17 16 15 14 13 12 11 10 9  8  7  6  5  4  3  2  1  0
            Digit:     0  0  6  1  4  1  4  1  1  2  3  4  5  6  7  8  9  ?
            Weight:    3  1  3  1  3  1  3  1  3  1  3  1  3  1  3  1  3
            Product:   0  0  18 1  12 1  12 1  3  2  9  4  15 6  21 8  27
            Sum: 140
            Check digit: (150 - 140) = 10 → 0
        """
        # Combine all digits except check digit
        digits = extension + company_prefix + serial_reference

        # GS1 uses right-to-left, alternating 3 and 1
        # Starting with 3 for the rightmost digit (position 0)
        total = 0
        for i, digit in enumerate(reversed(digits)):
            weight = 3 if i % 2 == 0 else 1
            total += int(digit) * weight

        # Calculate check digit
        remainder = total % 10
        if remainder == 0:
            check_digit = 0
        else:
            check_digit = 10 - remainder

        logger.debug(
            f"Check digit calculation for {digits}: "
            f"sum={total}, remainder={remainder}, check_digit={check_digit}"
        )

        return str(check_digit)

    @staticmethod
    def validate_sscc(sscc: SSCC) -> bool:
        """
        Validate an SSCC's check digit.

        Args:
            sscc: SSCC object to validate

        Returns:
            True if check digit is correct, False otherwise
        """
        calculated_check = SSCCGenerator._calculate_check_digit(
            extension=sscc.extension_digit,
            company_prefix=sscc.company_prefix,
            serial_reference=sscc.serial_reference
        )
        is_valid = calculated_check == sscc.check_digit

        if not is_valid:
            logger.warning(
                f"SSCC validation failed: {sscc.get_full_sscc()} "
                f"(expected check digit: {calculated_check}, got: {sscc.check_digit})"
            )

        return is_valid

    def peek_next_sscc(self) -> str:
        """
        Preview the next SSCC without incrementing the counter.

        Returns:
            String representation of the next SSCC
        """
        serial_str = str(self.current_serial).zfill(self.config.serial_padding)
        check_digit = self._calculate_check_digit(
            extension=self.config.extension_digit,
            company_prefix=self.config.company_prefix,
            serial_reference=serial_str
        )
        return f"{self.config.extension_digit}{self.config.company_prefix}{serial_str}{check_digit}"


def create_sscc_generator(
    company_prefix: str = "0614141",
    extension_digit: str = "0",
    serial_start: int = 1,
    serial_padding: int = 9
) -> SSCCGenerator:
    """
    Convenience function to create an SSCC generator.

    Args:
        company_prefix: GS1 company prefix (7-10 digits)
        extension_digit: Extension digit (0-9)
        serial_start: Starting serial number
        serial_padding: Zero-padding for serial reference

    Returns:
        Configured SSCCGenerator instance
    """
    config = SSCCConfig(
        company_prefix=company_prefix,
        extension_digit=extension_digit,
        serial_start=serial_start,
        serial_padding=serial_padding
    )
    return SSCCGenerator(config)
