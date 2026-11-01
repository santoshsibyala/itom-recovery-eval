import argparse
import json
import socket
from .runner import write_suite, verify_suite


def network_disabled(*args, **kwargs):
    raise RuntimeError('ITOM offline mode forbids network access')


def main():
    socket.socket.connect = network_disabled
    socket.socket.connect_ex = network_disabled
    socket.create_connection = network_disabled
    parser = argparse.ArgumentParser(description='Offline deterministic ITOM checks only; no paid execution')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'verify'):
        sub = commands.add_parser(name)
        sub.add_argument('--output', required=True)
    args = parser.parse_args()
    result = write_suite(args.output) if args.command == 'check' else verify_suite(args.output)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
