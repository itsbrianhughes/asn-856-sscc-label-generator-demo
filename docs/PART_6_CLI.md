# PART 6: CLI/UI Interface

## Overview

PART 6 implements a comprehensive command-line interface (CLI) for the ASN 856 + SSCC Label Generator using the Click framework. The CLI provides an intuitive way to process orders, generate EDI 856 ASNs, create shipping labels, and validate order files.

## Architecture

### CLI Framework

The CLI is built using **Click 8.1.7**, a Python package for creating command-line interfaces with:
- Command groups and subcommands
- Option parsing and validation
- Automatic help generation
- Progress bars and styled output
- File path validation

### Main Entry Point

**File:** `main.py`

The CLI is organized as a command group with multiple subcommands:
```
asn856
├── process          # Complete pipeline (cartonize → ASN → labels)
├── generate-asn     # Generate EDI 856 ASN only
├── generate-labels  # Generate shipping labels only
├── validate         # Validate order JSON file
└── examples         # Show usage examples
```

## Commands

### 1. Process Command

**Purpose:** Complete end-to-end order processing pipeline

**Usage:**
```bash
python main.py process --input order.json --output output/
```

**Options:**
- `--input, -i` (required): Path to order JSON file
- `--output, -o` (default: `output`): Output directory
- `--sender-id` (default: `SENDER`): EDI sender ID
- `--receiver-id` (default: `RECEIVER`): EDI receiver ID
- `--max-items` (default: `50`): Max items per carton
- `--max-weight` (default: `50.0`): Max weight per carton (lbs)
- `--skip-labels`: Skip label generation

**Process Flow:**
1. Load and validate order JSON
2. Cartonize order items with SSCC assignment
3. Generate EDI 856 ASN document
4. Create GS1-128 shipping labels (unless skipped)
5. Save all outputs to specified directory

**Example:**
```bash
python main.py process \
  --input examples/sample_orders/order_001.json \
  --output output/ \
  --sender-id ACME \
  --receiver-id CUSTOMER \
  --max-items 30 \
  --max-weight 75.0
```

**Output:**
```
output/
├── 856_SHIP-ORD-2025-001.txt
└── labels/
    ├── label_carton_1_006141410000000012.pdf
    ├── label_carton_2_006141410000000029.pdf
    └── label_carton_3_006141410000000036.pdf
```

### 2. Generate ASN Command

**Purpose:** Generate EDI 856 ASN document only (no labels)

**Usage:**
```bash
python main.py generate-asn --input order.json --output asn.txt
```

**Options:**
- `--input, -i` (required): Path to order JSON file
- `--output, -o` (required): Output ASN file path
- `--sender-id` (default: `SENDER`): EDI sender ID
- `--receiver-id` (default: `RECEIVER`): EDI receiver ID
- `--control-number`: EDI control number (auto-generated if not provided)

**Example:**
```bash
python main.py generate-asn \
  --input examples/sample_orders/order_001.json \
  --output my_asn_856.txt \
  --sender-id WAREHOUSE \
  --receiver-id RETAILER
```

**Output Format:** EDI X12 856 with segments:
```
ISA*00*...*~
GS*SH*...*~
ST*856*...*~
BSN*00*SHIP-ID*...*~
HL*1**S*1~
...
CTT*...*~
SE*...*~
GE*1*...*~
IEA*1*...*~
```

### 3. Generate Labels Command

**Purpose:** Generate shipping labels only (no ASN)

**Usage:**
```bash
python main.py generate-labels --input order.json --output labels/
```

**Options:**
- `--input, -i` (required): Path to order JSON file
- `--output, -o` (default: `output/labels`): Labels output directory
- `--no-contents`: Disable contents list on labels
- `--label-size` (default: `4x6`): Label size (4x6, 4x8, 6x8, letter)

**Example:**
```bash
python main.py generate-labels \
  --input examples/sample_orders/order_002_multi_carton.json \
  --output output/labels \
  --no-contents
```

**Output:** PDF files with GS1-128 barcodes:
- 4x6 inch shipping labels (standard)
- SSCC barcode with human-readable format
- Ship-to and ship-from addresses
- Carton sequence and weight
- Optional contents summary

### 4. Validate Command

**Purpose:** Validate order JSON file structure and data

**Usage:**
```bash
python main.py validate order.json
```

**Options:**
- `file` (required): Path to order JSON file to validate

**Validation Checks:**
- JSON syntax and structure
- Required fields present
- Data types correct
- State codes valid (2-letter US states)
- SKU format valid
- Quantities positive
- Dates valid
- Unique line numbers

**Example:**
```bash
python main.py validate examples/sample_orders/order_001.json
```

**Success Output:**
```
✅ Order file is valid!

Order Details:
  Order ID: ORD-2025-001
  PO Number: PO-ACME-12345
  Ship Date: 2025-12-15
  Items: 3 line items
  Total Units: 100 units
  Total Weight: 111.0 lbs
```

**Error Output:**
```
❌ Validation Error:

Error Details:
  Field: state
  Issue: State code must be 2 characters
  Value: TEX
```

### 5. Examples Command

**Purpose:** Show usage examples for all commands

**Usage:**
```bash
python main.py examples
```

**Output:** Comprehensive examples for each command with typical use cases.

## Configuration Options

### Cartonization Settings

Control how items are packed into cartons:

**Max Items Per Carton:**
```bash
python main.py process -i order.json --max-items 30
```
- Default: 50
- Range: 1-1000
- Use Case: Smaller values create more cartons

**Max Weight Per Carton:**
```bash
python main.py process -i order.json --max-weight 75.0
```
- Default: 50.0 lbs
- Range: 1.0-999.9 lbs
- Use Case: Adjust for carrier weight limits

### EDI Identifiers

Set trading partner identifiers for EDI interchange:

**Sender ID:**
```bash
python main.py generate-asn -i order.json --sender-id MYCOMPANY
```
- Used in: ISA06, GS02
- Format: Up to 15 characters
- Example: "ACME", "WAREHOUSE01"

**Receiver ID:**
```bash
python main.py generate-asn -i order.json --receiver-id CUSTOMER
```
- Used in: ISA08, GS03
- Format: Up to 15 characters
- Example: "RETAILER", "CUSTOMER42"

### Label Settings

Customize shipping label output:

**Label Size:**
```bash
python main.py generate-labels -i order.json --label-size 4x8
```
- Options: `4x6`, `4x8`, `6x8`, `letter`
- Default: `4x6` (standard shipping label)

**Contents Display:**
```bash
python main.py generate-labels -i order.json --no-contents
```
- Default: Contents shown
- Use `--no-contents` to hide SKU list on label

## Progress Indicators

The CLI provides real-time progress feedback:

**Cartonization Progress:**
```
Cartonizing order... ━━━━━━━━━━━━━━━━ 100%
```

**ASN Generation Progress:**
```
Generating ASN...
  ├─ Building hierarchy... ✓
  ├─ Generating segments... ✓
  └─ Writing file... ✓
```

**Label Rendering Progress:**
```
Rendering labels... ━━━━━━━━━━━━━━━━ 3/3
```

## Output Styling

The CLI uses colored output for better readability:

- ✅ **Green:** Success messages
- ❌ **Red:** Error messages
- ⚠️  **Yellow:** Warning messages
- ℹ️  **Blue:** Informational messages
- **Bold:** Important values and file paths

## Error Handling

### File Not Found
```
❌ Error: Order file not found
   Path: /path/to/nonexistent.json
```

### Validation Error
```
❌ Validation Error: Invalid order data

1 validation error for OrderInput
items
  field required (type=value_error.missing)
```

### Missing Dependencies
```
❌ Error: reportlab library required for label generation
   Install with: pip install reportlab python-barcode
```

## Integration with Python

The CLI can also be used programmatically:

```python
from main import cli
from click.testing import CliRunner

runner = CliRunner()
result = runner.invoke(cli, ['process', '--input', 'order.json'])
assert result.exit_code == 0
```

## Testing

**Test File:** `tests/test_cli.py`

Test coverage includes:
- Command help output
- Option parsing
- File validation
- Success scenarios
- Error scenarios
- Edge cases

**Run CLI Tests:**
```bash
pytest tests/test_cli.py -v
```

## Implementation Details

### Click Decorators

```python
@click.group()
@click.version_option(version='1.0.0')
def cli():
    """ASN 856 + SSCC Label Generator"""
    pass

@cli.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True))
@click.option('--output', '-o', default='output', type=click.Path())
def process(input, output):
    """Process complete order"""
    # Implementation
```

### File Path Validation

Click automatically validates file paths:
```python
type=click.Path(exists=True)  # Must exist
type=click.Path()             # Can be created
type=click.Path(dir_okay=False)  # Must be file
```

### Progress Bars

```python
with click.progressbar(items, label='Processing') as bar:
    for item in bar:
        process_item(item)
```

### Styled Output

```python
click.echo(click.style('✅ Success!', fg='green', bold=True))
click.echo(click.style('❌ Error!', fg='red', bold=True))
```

## Best Practices

### Input Validation

Always validate input files before processing:
```bash
# First validate
python main.py validate order.json

# Then process
python main.py process --input order.json
```

### Output Organization

Keep outputs organized by date or order ID:
```bash
OUTPUT_DIR="output/$(date +%Y%m%d)"
python main.py process --input order.json --output "$OUTPUT_DIR"
```

### Batch Processing

Process multiple orders in a loop:
```bash
for order_file in orders/*.json; do
    python main.py process --input "$order_file" --output "output/"
done
```

### Error Logging

Redirect errors to log files:
```bash
python main.py process --input order.json 2> error.log
```

## Future Enhancements

Potential CLI improvements for future versions:

1. **Batch Mode:** Process multiple orders at once
2. **Watch Mode:** Monitor directory for new orders
3. **Dry Run:** Preview operations without generating files
4. **JSON Output:** Machine-readable output format
5. **Configuration File:** Store default options in YAML/JSON
6. **Web UI:** Optional Streamlit interface
7. **API Mode:** RESTful API server
8. **Database Integration:** Store orders and outputs

## Related Documentation

- [Quick Start Guide](QUICKSTART.md) - Getting started tutorial
- [PART 1: Data Models](PART_1_DATA_MODELS.md) - Data structures
- [PART 2: Cartonization](PART_2_CARTONIZATION.md) - Packing logic
- [PART 3: ASN Builder](PART_3_ASN_BUILDER.md) - EDI generation
- [PART 5: Label Renderer](PART_5_LABEL_RENDERER.md) - Label generation

## Summary

PART 6 provides a production-ready command-line interface that makes the ASN 856 + SSCC Label Generator accessible to users without programming knowledge. The CLI wraps all core functionality in an intuitive, well-documented interface with comprehensive error handling and helpful feedback.

**Status:** ✅ **COMPLETE** — Full CLI implementation with all commands operational

**Next:** PART 7 — Final packaging, documentation, and GitHub preparation
