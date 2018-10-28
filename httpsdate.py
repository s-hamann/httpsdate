#!/usr/bin/env python3
"""httpsdate.py is a script for secure time synchronisation"""
__version__ = '0.1.0'

import argparse
import os
import prctl
import pwd
import sys
import time
import urllib.request

from datetime import datetime, timezone
from statistics import median


# Exit codes
E_PRIV = 3
E_NOTIME = 4
E_NOTENOUGHTIME = 5
E_LARGEOFFSET = 6

# Set a nicer title than 'python3'.
prctl.set_name('httpsdate.py')


def drop_privileges(user):
    """Drop all capabilities except CAP_SYS_TIME from the permitted and
    the bounding set and switch to the given user.

    :user: name of the user to switch to
    :returns: nothing
    """
    # Get the numeric UID and GID of the given user.
    uid = pwd.getpwnam(user).pw_uid
    gid = pwd.getpwnam(user).pw_gid

    # Keep permitted capabilities when changing the UID.
    prctl.securebits.keep_caps = True

    # Limit the bounding set to CAP_SYS_TIME.
    prctl.capbset.limit(prctl.CAP_SYS_TIME)

    # Change user and group.
    os.setgroups([gid])
    os.setgid(gid)
    os.setuid(uid)

    # Limit the permitted set to CAP_SYS_TIME.
    prctl.cap_permitted.limit(prctl.CAP_SYS_TIME)
    # Activate CAP_SYS_TIME.
    prctl.cap_effective.sys_time = True

    # Disallow gaining new capabilities.
    prctl.set_no_new_privs(1)


def get_date(host):
    """Send a HEAD request via HTTPS to the given host and return the
    contents of the Date header.

    :host: the FQDN to get the date from
    :returns: datetime object containing the data from the Date header
    """
    request = urllib.request.Request('https://{}/'.format(host), method='HEAD')
    request.add_header('User-Agent', 'httpsdate.py')
    response = urllib.request.urlopen(request)
    date = datetime.strptime(response.info()['Date'],
                             '%a, %d %b %Y %H:%M:%S GMT')
    return date


parser = argparse.ArgumentParser(
    description='Set the system clock to a date and time obtained from one or '
    'more HTTPS servers. Needs to be run with CAP_SYS_TIME, but drops '
    'unnecessary privileges when started as root.')
parser.add_argument('-n', '--dry-run', default=False, action='store_true',
                    help='do not actually set the system clock')
parser.add_argument('-u', '--user', default='nobody',
                    help='when started with high privileges, '
                    'run as this user instead (default: %(default)s)')
parser.add_argument('--max-adjust', metavar='seconds', type=int,
                    help='do not change the clock more than this many seconds')
parser.add_argument('--max-failed', metavar='N', type=int,
                    help='do not change the clock if more than N servers '
                    'failed to send a usable date and time')
parser.add_argument('-q', '--quiet', default=False, action='store_true',
                    help='do not show warnings and adjustment information')
parser.add_argument('host', nargs='+',
                    help='get the time from the Date header of these '
                    'HTTPS servers')
args = parser.parse_args()


# Check if we have sufficient privileges.
if not prctl.cap_permitted.sys_time and not args.dry_run:
    print('Insufficient privileges to set the clock.')
    print('Please run as root or with CAP_SYS_TIME.')
    sys.exit(E_PRIV)

# Check if we have more privileges than needed.
if prctl.cap_effective.setpcap:
    # This actually only checks for one of the capabilities required to drop
    # privileges. But having any capability besides CAP_SYS_TIME probably
    # means that we have all of them.
    drop_privileges(args.user)

# Get the time from all hosts.
times = []
for host in args.host:
    try:
        t = get_date(host)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
        if not args.quiet:
            print('Warning: Could not get time from {host}: {error}'.
                  format(host=host, error=str(e)), file=sys.stderr)
        continue
    times.append(t)

succeeded = len(times)
failed = len(args.host) - len(times)

# Check that at least one host was usable.
if not succeeded:
    print('Error: Could not get time from any host.', file=sys.stderr)
    sys.exit(E_NOTIME)

# Check that no more than --max-failed hosts failed.
if (args.max_failed is not None and failed > args.max_failed):
    print('Error: {} hosts failed. No more than {} are allowed.'.
          format(failed, args.max_failed), file=sys.stderr)
    sys.exit(E_NOTENOUGHTIME)

# Sort the times.
times.sort()

# Calculate the median of all received times.
# Since median() can not really handle datetime objects, we convert them
# to UNIX timestamps and convert the result back to datetime, this time
# adding timezone information.
new_time = (datetime.fromtimestamp(median([t.timestamp() for t in times])).
            replace(tzinfo=timezone.utc))

now = datetime.now(tz=timezone.utc)
adjustment = new_time - now
interval = times[-1] - times[0]

# Check if the new time is close enough to the current time.
if args.max_adjust and args.max_adjust < abs(adjustment.total_seconds()):
    print('Error: Offset between local and remote clock is {:.2f} seconds. '
          'Only {} seconds are allowed.'.
          format(adjustment.total_seconds(), args.max_adjust))
    sys.exit(E_LARGEOFFSET)

if not args.quiet:
    # Display a short summary about how much the time changes and
    # how much the remote clocks agree.
    print('Time adjustment: {:.2f} seconds'.format(adjustment.total_seconds()))
    print('{} remote clocks returned usable time information, {} did not.'.
          format(succeeded, failed))
    if succeeded > 1:
        print('Remote clocks deviate by {}'.format(interval))

if not args.dry_run:
    # Actually set the system clock to the new time.
    time.clock_settime(time.CLOCK_REALTIME, new_time.timestamp())
