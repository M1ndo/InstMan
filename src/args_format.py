#!/usr/bin/env python3
import argparse

class FormatAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        mapping = {
            'stories': True,
            'highlights': True,
            'posts': True,
            'comments': True,
        }

        components = [s.strip() for s in values.split('+')]
        mapping = {c: v for c, v in mapping.items() if c in components}
        flags = [mapping.get(c, False) for c in ['stories', 'highlights', 'posts', 'comments']] + [False] * (4 - len(mapping))
        setattr(namespace, 'stories', flags[0])
        setattr(namespace, 'highlights', flags[1])
        setattr(namespace, 'posts', flags[2])
        setattr(namespace, 'comments', flags[3])

def arguments():
    """ Require and optional arguments """
    parser = argparse.ArgumentParser(description="InstMan An Account Monitoring Tool", add_help=True)
    parser.add_argument('-c', '--change', action="store_true", help="Mark changes of an account", dest="change")
    parser.add_argument('-ignore-count', action="store_true", help="Ignore followers/following count", dest="ignore_count")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--user', type=str, nargs='+', help="Username(s) to do actions to", dest="user")
    group.add_argument('-I', '--users-file', type=argparse.FileType('r'), help="File that contains Username(s) to do actions to", dest='users')
    parser.add_argument('-u', '--username', type=str, help="Username to authenticate with", dest="auth")
    parser.add_argument('-p', '--info', action="store_true", help="Print information of a user", dest="print")
    parser.add_argument('-m', '--media', action="store_true", help="List username media", dest="media")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('-f', '--format', help='Format string for specifying media types', action=FormatAction)
    parser.add_argument('-D', '--download', action="store_true", help='Download media types', dest="download")
    return parser
