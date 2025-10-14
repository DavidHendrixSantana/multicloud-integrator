"""
Command Line Interface for the Multi-Cloud File Transfer Tool.
"""
import os
import sys
import json
from pathlib import Path
from typing import List, Tuple

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from transfer_manager import MultiCloudTransferManager
from connectors import list_supported_providers
from config import config
from logger import setup_logging, console
from utils import format_bytes, calculate_transfer_speed

# Initialize components
logger = setup_logging()
transfer_manager = MultiCloudTransferManager()

@click.group()
@click.version_option(version='1.0.0')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """
    Multi-Cloud File Transfer CLI Tool
    
    Transfer files seamlessly between AWS S3, Azure Blob Storage, and Google Cloud Storage.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")

@cli.command()
def test():
    """Test connections to all configured cloud providers."""
    console.print("[bold blue]Testing cloud provider connections...[/bold blue]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Testing connections...", total=None)
        results = transfer_manager.test_connections()
    
    # Create results table
    table = Table(title="Connection Test Results")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Configuration", justify="center")
    
    for provider, status in results.items():
        if status is None:
            status_text = "[yellow]Not Configured[/yellow]"
            config_text = "[red]Missing[/red]"
        elif status:
            status_text = "[green]✓ Connected[/green]"
            config_text = "[green]✓ Valid[/green]"
        else:
            status_text = "[red]✗ Failed[/red]"
            config_text = "[yellow]Check Config[/yellow]"
        
        table.add_row(provider, status_text, config_text)
    
    console.print(table)
    
    # Show configuration hints
    if any(status is None for status in results.values()):
        console.print("\n[yellow]Configuration Required:[/yellow]")
        console.print("Copy .env.example to .env and configure your cloud provider credentials.")

@cli.command()
@click.argument('cloud_url')
@click.option('--prefix', default='', help='Filter files by prefix')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list(cloud_url, prefix, output_format):
    """List files in cloud storage."""
    try:
        console.print(f"[blue]Listing files from {cloud_url}[/blue]")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Fetching file list...", total=None)
            files = transfer_manager.list_files(cloud_url, prefix)
        
        if not files:
            console.print("[yellow]No files found.[/yellow]")
            return
        
        if output_format == 'json':
            file_data = []
            for file_info in files:
                file_data.append({
                    'name': file_info.name,
                    'size': file_info.size,
                    'size_formatted': format_bytes(file_info.size),
                    'last_modified': file_info.last_modified,
                    'content_type': file_info.content_type,
                    'etag': file_info.etag
                })
            console.print_json(json.dumps(file_data, indent=2))
        else:
            # Table format
            table = Table(title=f"Files in {cloud_url}")
            table.add_column("Name", style="cyan")
            table.add_column("Size", justify="right")
            table.add_column("Last Modified", style="dim")
            table.add_column("Type", style="green")
            
            for file_info in files:
                table.add_row(
                    file_info.name,
                    format_bytes(file_info.size),
                    file_info.last_modified[:19] if file_info.last_modified else 'Unknown',
                    file_info.content_type or 'Unknown'
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(files)} files[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

@cli.command()
@click.argument('source_url')
@click.argument('dest_url')
@click.option('--force', is_flag=True, help='Overwrite destination if exists')
@click.option('--metadata', help='JSON metadata to attach (upload only)')
def copy(source_url, dest_url, force, metadata):
    """Copy a file between cloud storage providers or upload/download."""
    try:
        # Parse metadata if provided
        extra_args = {}
        if metadata:
            try:
                extra_args['metadata'] = json.loads(metadata)
            except json.JSONDecodeError:
                console.print("[red]Error: Invalid JSON metadata[/red]")
                sys.exit(1)
        
        # Check if destination exists (if not force)
        if not force:
            try:
                if transfer_manager.file_exists(dest_url):
                    if not Confirm.ask(f"Destination {dest_url} exists. Overwrite?"):
                        console.print("[yellow]Operation cancelled.[/yellow]")
                        return
            except:
                pass  # Ignore errors checking existence
        
        console.print(f"[blue]Copying {source_url} -> {dest_url}[/blue]")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Transferring file...", total=None)
            
            # Determine operation type
            if source_url.startswith(('s3://', 'azure://', 'gcs://', 'gs://')):
                if dest_url.startswith(('s3://', 'azure://', 'gcs://', 'gs://')):
                    # Cloud to cloud
                    result = transfer_manager.copy_file_direct(source_url, dest_url, **extra_args)
                else:
                    # Cloud to local (download)
                    result = transfer_manager.download_file(source_url, dest_url, **extra_args)
            else:
                # Local to cloud (upload)
                result = transfer_manager.upload_file(source_url, dest_url, **extra_args)
        
        # Display results
        if result.success:
            console.print("[green]✓ Transfer completed successfully[/green]")
            
            # Create results table
            table = Table(title="Transfer Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Source", result.source_path)
            table.add_row("Destination", result.destination_path)
            table.add_row("Bytes Transferred", format_bytes(result.bytes_transferred))
            table.add_row("Duration", f"{result.duration_seconds:.2f} seconds")
            
            if result.duration_seconds > 0:
                speed = calculate_transfer_speed(result.bytes_transferred, result.duration_seconds)
                table.add_row("Average Speed", speed)
            
            console.print(table)
        else:
            console.print(f"[red]✗ Transfer failed: {result.error_message}[/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def batch(file_path, output_format):
    """
    Perform batch transfers from a JSON file.
    
    JSON format: [{"source": "s3://...", "destination": "azure://..."}]
    """
    try:
        with open(file_path, 'r') as f:
            transfers_data = json.load(f)
        
        transfers = []
        for item in transfers_data:
            if 'source' not in item or 'destination' not in item:
                console.print("[red]Error: Each transfer must have 'source' and 'destination'[/red]")
                sys.exit(1)
            transfers.append((item['source'], item['destination']))
        
        console.print(f"[blue]Starting batch transfer of {len(transfers)} files...[/blue]")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Processing batch transfers...", total=len(transfers))
            results = transfer_manager.batch_copy(transfers)
            progress.update(task, completed=len(transfers))
        
        # Display results
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_bytes = sum(r.bytes_transferred for r in results if r.success)
        
        if output_format == 'json':
            results_data = []
            for result in results:
                results_data.append({
                    'success': result.success,
                    'source': result.source_path,
                    'destination': result.destination_path,
                    'bytes_transferred': result.bytes_transferred,
                    'duration_seconds': result.duration_seconds,
                    'error_message': result.error_message
                })
            console.print_json(json.dumps(results_data, indent=2))
        else:
            # Summary table
            table = Table(title="Batch Transfer Summary")
            table.add_column("Status", justify="center")
            table.add_column("Count", justify="right")
            
            table.add_row("[green]Successful[/green]", str(successful))
            table.add_row("[red]Failed[/red]", str(failed))
            table.add_row("[blue]Total Transferred[/blue]", format_bytes(total_bytes))
            
            console.print(table)
            
            # Show failed transfers if any
            if failed > 0:
                console.print("\n[red]Failed Transfers:[/red]")
                for result in results:
                    if not result.success:
                        console.print(f"  [red]✗[/red] {result.source_path} -> {result.destination_path}")
                        console.print(f"    [dim]{result.error_message}[/dim]")
        
        if failed > 0:
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

@cli.command()
@click.argument('cloud_url')
def info(cloud_url):
    """Get information about a file in cloud storage."""
    try:
        console.print(f"[blue]Getting file information for {cloud_url}[/blue]")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Fetching file info...", total=None)
            file_info = transfer_manager.get_file_info(cloud_url)
        
        # Display file information
        table = Table(title=f"File Information: {cloud_url}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Name", file_info.name)
        table.add_row("Size", format_bytes(file_info.size))
        table.add_row("Last Modified", file_info.last_modified)
        table.add_row("Content Type", file_info.content_type or "Unknown")
        table.add_row("ETag", file_info.etag or "Unknown")
        
        if file_info.metadata:
            table.add_row("Metadata", json.dumps(file_info.metadata, indent=2))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

@cli.command()
@click.argument('cloud_url')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def delete(cloud_url, force):
    """Delete a file from cloud storage."""
    try:
        if not force:
            if not Confirm.ask(f"Are you sure you want to delete {cloud_url}?"):
                console.print("[yellow]Operation cancelled.[/yellow]")
                return
        
        console.print(f"[red]Deleting {cloud_url}[/red]")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Deleting file...", total=None)
            success = transfer_manager.delete_file(cloud_url)
        
        if success:
            console.print("[green]✓ File deleted successfully[/green]")
        else:
            console.print("[red]✗ Failed to delete file[/red]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

@cli.command()
def providers():
    """List supported cloud providers."""
    table = Table(title="Supported Cloud Providers")
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("URL Format", style="green")
    table.add_column("Description", style="white")
    
    providers = list_supported_providers()
    url_formats = {
        'AWS S3': 's3://bucket/path/to/file',
        'Microsoft Azure Blob Storage': 'azure://container/path/to/file',
        'Google Cloud Platform Storage': 'gcs://bucket/path/to/file'
    }
    
    for provider_enum, provider_name, description in providers:
        url_format = url_formats.get(description, 'N/A')
        table.add_row(provider_name, url_format, description)
    
    console.print(table)

@cli.command()
def config_check():
    """Check configuration status."""
    table = Table(title="Configuration Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Required Variables", style="dim")
    
    # AWS
    aws_status = "[green]✓ Configured[/green]" if config.validate_aws_config() else "[red]✗ Missing[/red]"
    table.add_row("AWS S3", aws_status, "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
    
    # Azure
    azure_status = "[green]✓ Configured[/green]" if config.validate_azure_config() else "[red]✗ Missing[/red]"
    table.add_row("Azure Blob", azure_status, "AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY")
    
    # GCP
    gcp_status = "[green]✓ Configured[/green]" if config.validate_gcp_config() else "[red]✗ Missing[/red]"
    table.add_row("GCP Storage", gcp_status, "GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT_ID")
    
    console.print(table)
    
    # Show .env file status
    env_file = Path(".env")
    if env_file.exists():
        console.print(f"\n[green]✓ .env file found at {env_file.absolute()}[/green]")
    else:
        console.print(f"\n[yellow]⚠ .env file not found. Copy .env.example to .env and configure.[/yellow]")

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        sys.exit(1)
    finally:
        # Cleanup
        transfer_manager.cleanup()
