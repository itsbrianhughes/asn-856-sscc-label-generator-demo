#!/usr/bin/env python3
"""
Main CLI Entry Point
====================
Command-line interface for ASN 856 + SSCC Label Generator.

Usage:
    python main.py process --input order.json
    python main.py generate-asn --input order.json --output output/
    python main.py generate-labels --input order.json --output output/labels/
    python main.py --help

Author: Integration Engineering Team
"""

import sys
import click
import os
from pathlib import Path
from datetime import datetime
import json
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.input_models import OrderInput
from src.cartonization.engine import CartonizationEngine
from src.cartonization.config import CartonizationConfig
from src.asn_builder.builder import ASNBuilder
from src.label_generator.builder import LabelBuilder
from src.models.label_models import LabelConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0', prog_name='ASN Generator')
def cli():
    """
    ASN 856 + SSCC Label Generator

    A complete system for generating EDI 856 Advance Ship Notices
    and GS1-compliant shipping labels.

    \b
    Workflow:
      Order JSON → Cartonization → ASN 856 → PDF Labels

    \b
    Example:
      python main.py process --input order.json --output output/
    """
    pass


@cli.command()
@click.option(
    '--input', '-i',
    required=True,
    type=str,
    help='Input order JSON file'
)
@click.option(
    '--output', '-o',
    default='output',
    type=click.Path(),
    help='Output directory (default: output/)'
)
@click.option(
    '--sender-id',
    default='SENDER',
    help='EDI sender ID (default: SENDER)'
)
@click.option(
    '--receiver-id',
    default='RECEIVER',
    help='EDI receiver ID (default: RECEIVER)'
)
@click.option(
    '--max-items',
    type=int,
    default=50,
    help='Max items per carton (default: 50)'
)
@click.option(
    '--max-weight',
    type=float,
    default=50.0,
    help='Max weight per carton in lbs (default: 50.0)'
)
@click.option(
    '--skip-labels',
    is_flag=True,
    help='Skip label generation'
)
def process(input, output, sender_id, receiver_id, max_items, max_weight, skip_labels):
    """
    Process complete order: cartonize, generate ASN, and create labels.

    This is the main command that runs the entire pipeline.

    \b
    Example:
      python main.py process -i examples/sample_orders/order_001.json
    """
    try:
        click.echo(click.style('\n🚀 ASN Generator - Complete Processing Pipeline', bold=True, fg='cyan'))
        click.echo('=' * 70)

        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Load Order
        click.echo(click.style('\n📥 Step 1: Loading Order', bold=True))
        click.echo(f'   Input: {input}')

        with open(input) as f:
            order_data = json.load(f)

        order = OrderInput(**order_data)
        click.echo(f'   ✅ Order: {order.order_id}')
        click.echo(f'   PO: {order.purchase_order}')
        click.echo(f'   Items: {len(order.items)} line items, {sum(i.quantity for i in order.items)} units')

        # Step 2: Cartonization
        click.echo(click.style('\n📦 Step 2: Cartonization', bold=True))
        click.echo(f'   Max items per carton: {max_items}')
        click.echo(f'   Max weight per carton: {max_weight} lbs')

        carton_config = CartonizationConfig(
            max_items_per_carton=max_items,
            max_weight_per_carton=max_weight
        )

        with click.progressbar(length=1, label='   Cartonizing') as bar:
            engine = CartonizationEngine(carton_config)
            shipment_package = engine.cartonize_order(order)
            bar.update(1)

        shipment = shipment_package.shipment
        click.echo(f'   ✅ Created {shipment.total_cartons} carton(s), {shipment.total_weight:.2f} lbs')

        # Step 3: ASN Generation
        click.echo(click.style('\n📄 Step 3: ASN Generation', bold=True))

        asn_builder = ASNBuilder()

        with click.progressbar(length=1, label='   Generating ASN') as bar:
            edi_content = asn_builder.build_asn(
                shipment_package,
                sender_id=sender_id,
                receiver_id=receiver_id
            )
            bar.update(1)

        # Save ASN
        asn_file = output_path / f'856_{shipment.shipment_id}.txt'
        with open(asn_file, 'w') as f:
            f.write(edi_content)

        segment_count = asn_builder.count_segments(edi_content)
        click.echo(f'   ✅ ASN saved: {asn_file.name}')
        click.echo(f'   Segments: {segment_count}, Size: {len(edi_content)} bytes')

        # Step 4: Label Generation
        if not skip_labels:
            click.echo(click.style('\n🏷️  Step 4: Label Generation', bold=True))

            try:
                labels_dir = output_path / 'labels'
                labels_dir.mkdir(exist_ok=True)

                label_builder = LabelBuilder()

                with click.progressbar(
                    length=shipment.total_cartons,
                    label='   Generating labels'
                ) as bar:
                    label_batch = label_builder.render_labels_for_shipment(
                        shipment_package,
                        str(labels_dir)
                    )
                    bar.update(shipment.total_cartons)

                click.echo(f'   ✅ Generated {label_batch.total_labels} label(s)')
                click.echo(f'   Directory: {labels_dir}')

            except ImportError as e:
                click.echo(click.style(f'   ⚠️  Label generation skipped: {e}', fg='yellow'))
                click.echo('   Install: pip install reportlab python-barcode')
        else:
            click.echo(click.style('\n🏷️  Step 4: Label Generation', bold=True))
            click.echo('   ⏭️  Skipped (--skip-labels)')

        # Summary
        click.echo(click.style('\n✅ Processing Complete!', bold=True, fg='green'))
        click.echo('\n📊 Output Summary:')
        click.echo(f'   Output directory: {output_path}')
        click.echo(f'   ├─ ASN: {asn_file.name}')
        if not skip_labels:
            click.echo(f'   └─ Labels: labels/ ({shipment.total_cartons} files)')

        click.echo('\n' + '=' * 70)

    except Exception as e:
        click.echo(click.style(f'\n❌ Error: {e}', fg='red', bold=True))
        logger.exception('Processing failed')
        sys.exit(1)


@cli.command()
@click.option(
    '--input', '-i',
    required=True,
    type=str,
    help='Input order JSON file'
)
@click.option(
    '--output', '-o',
    required=True,
    type=click.Path(),
    help='Output ASN file path'
)
@click.option(
    '--sender-id',
    default='SENDER',
    help='EDI sender ID'
)
@click.option(
    '--receiver-id',
    default='RECEIVER',
    help='EDI receiver ID'
)
@click.option(
    '--max-items',
    type=int,
    default=50,
    help='Max items per carton'
)
def generate_asn(input, output, sender_id, receiver_id, max_items):
    """
    Generate EDI 856 ASN only (no labels).

    \b
    Example:
      python main.py generate-asn -i order.json -o output/856.txt
    """
    try:
        click.echo(click.style('\n📄 Generating ASN', bold=True, fg='cyan'))

        # Load order
        with open(input) as f:
            order_data = json.load(f)
        order = OrderInput(**order_data)

        # Cartonize
        config = CartonizationConfig(max_items_per_carton=max_items)
        engine = CartonizationEngine(config)
        shipment_package = engine.cartonize_order(order)

        # Generate ASN
        asn_builder = ASNBuilder()
        edi_content = asn_builder.build_asn(
            shipment_package,
            sender_id=sender_id,
            receiver_id=receiver_id
        )

        # Save
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(edi_content)

        click.echo(f'✅ ASN saved: {output_path}')
        click.echo(f'   Segments: {asn_builder.count_segments(edi_content)}')

    except Exception as e:
        click.echo(click.style(f'❌ Error: {e}', fg='red'))
        sys.exit(1)


@cli.command()
@click.option(
    '--input', '-i',
    required=True,
    type=str,
    help='Input order JSON file'
)
@click.option(
    '--output', '-o',
    required=True,
    type=click.Path(),
    help='Output directory for labels'
)
@click.option(
    '--max-items',
    type=int,
    default=50,
    help='Max items per carton'
)
@click.option(
    '--no-contents',
    is_flag=True,
    default=False,
    help='Hide contents list on labels'
)
def generate_labels(input, output, max_items, no_contents):
    """
    Generate shipping labels only (no ASN).

    \b
    Example:
      python main.py generate-labels -i order.json -o output/labels/
    """
    try:
        click.echo(click.style('\n🏷️  Generating Labels', bold=True, fg='cyan'))

        # Load order
        with open(input) as f:
            order_data = json.load(f)
        order = OrderInput(**order_data)

        # Cartonize
        config = CartonizationConfig(max_items_per_carton=max_items)
        engine = CartonizationEngine(config)
        shipment_package = engine.cartonize_order(order)

        # Generate labels
        label_config = LabelConfig(show_contents=not no_contents)
        label_builder = LabelBuilder(label_config)

        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        with click.progressbar(
            length=shipment_package.shipment.total_cartons,
            label='Generating'
        ) as bar:
            label_batch = label_builder.render_labels_for_shipment(
                shipment_package,
                str(output_path)
            )
            bar.update(shipment_package.shipment.total_cartons)

        click.echo(f'✅ Generated {label_batch.total_labels} label(s)')
        click.echo(f'   Directory: {output_path}')

    except ImportError as e:
        click.echo(click.style(f'❌ Error: {e}', fg='red'))
        click.echo('Install: pip install reportlab python-barcode')
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f'❌ Error: {e}', fg='red'))
        sys.exit(1)


@cli.command()
@click.argument('order_file', type=str)
def validate(order_file):
    """
    Validate an order JSON file.

    \b
    Example:
      python main.py validate examples/sample_orders/order_001.json
    """
    try:
        click.echo(click.style('\n🔍 Validating Order', bold=True, fg='cyan'))
        click.echo(f'   File: {order_file}')

        with open(order_file) as f:
            order_data = json.load(f)

        order = OrderInput(**order_data)

        click.echo(click.style('\n✅ Validation Passed', fg='green'))
        click.echo(f'\n📋 Order Details:')
        click.echo(f'   Order ID: {order.order_id}')
        click.echo(f'   PO Number: {order.purchase_order}')
        click.echo(f'   Ship Date: {order.ship_date}')
        click.echo(f'   Ship From: {order.ship_from.name}, {order.ship_from.city}, {order.ship_from.state}')
        click.echo(f'   Ship To: {order.ship_to.name}, {order.ship_to.city}, {order.ship_to.state}')
        click.echo(f'   Carrier: {order.carrier_code or "N/A"}')
        click.echo(f'\n📦 Line Items: {len(order.items)}')

        total_qty = sum(item.quantity for item in order.items)
        total_weight = sum(item.quantity * (item.unit_weight or 0) for item in order.items)

        for item in order.items:
            click.echo(f'   {item.line_number}. {item.sku}: {item.description}')
            click.echo(f'      Quantity: {item.quantity} {item.uom}, Weight: {item.unit_weight or "N/A"} lbs/unit')

        click.echo(f'\n📊 Totals:')
        click.echo(f'   Total Units: {total_qty}')
        click.echo(f'   Total Weight: {total_weight:.2f} lbs')

    except Exception as e:
        click.echo(click.style(f'\n❌ Validation Failed: {e}', fg='red'))
        sys.exit(1)


@cli.command()
def examples():
    """
    Show usage examples.
    """
    click.echo(click.style('\n📚 Usage Examples', bold=True, fg='cyan'))
    click.echo('=' * 70)

    examples_text = """
1. Process Complete Order (ASN + Labels):
   python main.py process --input examples/sample_orders/order_001.json

2. Process with Custom Carton Limits:
   python main.py process -i order.json --max-items 30 --max-weight 75.0

3. Generate ASN Only:
   python main.py generate-asn -i order.json -o output/856.txt

4. Generate Labels Only:
   python main.py generate-labels -i order.json -o output/labels/

5. Validate Order File:
   python main.py validate examples/sample_orders/order_001.json

6. Process Without Labels:
   python main.py process -i order.json --skip-labels

7. Custom EDI IDs:
   python main.py process -i order.json --sender-id ACME --receiver-id BIGBOX

8. Get Help:
   python main.py --help
   python main.py process --help
    """

    click.echo(examples_text)


if __name__ == '__main__':
    cli()
