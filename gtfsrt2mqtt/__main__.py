import click
import logging

from gtfsrt2mqtt.publisher import GTFSRealtimePublisher

logging.basicConfig(
    level=logging.INFO, 
    format= '[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--config', '-c', default=None, help='Configuration file for the publisher')
def run(config):
    with GTFSRealtimePublisher(config) as publisher:
        publisher.run()

if __name__ == '__main__':
    cli()