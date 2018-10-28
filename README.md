httpsdate.py
============

This is a (fairly) simple python script that sets the system clock to a value obtained from a set of HTTPS servers.
This provides a simple and secure, but not very accurate method of time synchronisation.

Why?
====

Several of today's security technologies assume a correct local clock.
One example is certificate expiration.

Unfortunately, the choice of secure and reliable clock synchronisation protocols is scarce.
A discussion of the sorry state of today's options can be found in https://blog.hboeck.de/archives/890-In-Search-of-a-Secure-Time-Source.html by @hannob.
The author also came up with a simple, yet effective method of securely synchronising the system clock with a remote server.

This method and the script [`httpstime`](https://github.com/hannob/httpstime) are what inspired `httpsdate.py`.
It was written to overcome some of the limitations imposed by the simplistic design of `httpstime`:

1. `httpsdate.py` automatically runs with minimal privileges.
2. `httpsdate.py` does not necessarily rely on a single server to provide the correct time.

How does it work?
=================

`httpsdate.py` queries one or more HTTPS servers for the timestamp in the `Date` HTTP header.
The system clock is then set to the median of the timestamps obtained this way.

As long as more than half of the timestamps are correct, the resulting system time is correct.
It may however, loose a few seconds of accuracy, due to the limitations imposed by the very simplistic protocol.

`httpsdate.py` exits when it is done.
To keep the system clock in sync over a extended period of time, simply run `httpsdate.py` regularly, for example as a cron job or systemd timer.

How to use it
=============

The most simple way to use it is to run something like the following command as `root`:
```sh
httpsdate.py www.ptb.de
```
This will get the current time from [www.ptb.de](https://www.ptb.de/) and set the local system clock to match it.
The console output looks something like this:
```
Time adjustment: 0.43 seconds
1 remote clocks returned usable time information, 0 did not.
```

As mentioned above, it is also possible to query multiple servers:
```sh
httpsdate.py www.ptb.de www.metas.ch
```
See [below](#Rogue Servers) on why one would want to do that.

Before explaining the other options of `httpsdate.py`, let's have a look at the help message:

```
usage: httpsdate.py [-h] [-n] [-u USER] [--max-adjust seconds] [-q]
                    host [host ...]

Set the system clock to a date and time obtained from one or more HTTPS
servers. Needs to be run with CAP_SYS_TIME, but drops unnecessary privileges
when started as root.

positional arguments:
  host                  get the time from the Date header of these HTTPS
                        servers

optional arguments:
  -h, --help            show this help message and exit
  -n, --dry-run         do not actually set the system clock
  -u USER, --user USER  when started with high privileges, run as this user
                        instead (default: nobody)
  --max-adjust seconds  do not change the clock more than this many seconds
  --max-failed N        do not change the clock if more than N servers failed
                        to send a usable date and time
  -q, --quiet           do not show warnings and adjustment information
```

If `httpsdate.py` is invoked with `root` privileges, it will automatically drop all privileges except `CAP_SYS_TIME` (which is required for setting the system clock) and switch to a non-privileged user.
Use `--user` to specify what user account to switch to.  
It is not necessary to run `httpsdate.py` as `root`.
Running it with only `CAP_SYS_TIME` is sufficient.
Without further privileges, it can obviously not switch the user and silently ignores the `--user` option, if provided.

Use `--dry-run` in order to just see what would happen but not actually change the system clock.

When invoked with `--quiet`, `httpsdate.py` suppresses non-error messages.
Non-error messages are:
* warnings about unusable servers, e.g. due to certificate validation errors
* the summary at the end, which can help estimating the reliability of the new system time

Usually, the system time can be trusted to be not too far off from the correct time.
To reflect that, the option `--max-adjust` can be used.
It instructs `httpsdate.py` to bail out without modifying the system clock if the new time is too far from the current system time.
Together with infrequent synchronisations, this helps prevent malicious servers from deliberately changing the system clock (much).
Reasonable values are a few minutes or seconds, depending on the usual clock drift and the synchronisation frequency.

Similarly, `--max-failed` limits the fault tolerance of `httpsdate.py`.
It will not change the system clock if more than this many remote servers failed to send a usable time.
Reasons for not getting a usable time include invalid X.509 certificates, TLS parameter incompatibilities or missing or invalid `Date` headers.

Requirements
============

* Linux Kernel 3.5 or newer
* Python 3.4.3 or newer
* python-prctl
* a moderately correct system time to begin with (a few months off should be OK)

`httpsdate.py` should also run on Python 3.3.
Before 3.4.3 Python did not validate HTTPS certificates by default, thus rendering HTTPS vulnerable to man-in-the-middle attacks, unless the respective code sets up validation.
`httpsdate.py` relies on Python do the right thing and should therefore not be used with Python versions before 3.4.3 (unless they are patched, that is).

In case of doubt, one can run
```sh
httpsdate.py -n self-signed.badssl.com
```
or
```sh
python3 -c 'from urllib.request import urlopen; urlopen("https://self-signed.badssl.com")'
```
If either command throws an error containing `CERTIFICATE_VERIFY_FAILED`, all is well and Python *does* validate certificates.

Installation
============

No installation is required.
It is enough to download and run `httpsdate.py`.

For convenience, `httpsdate.py` can also be installed using `pip`:
```sh
pip install httpsdate
```

Security Considerations
=======================

Man-in-the-Middle attacks
-------------------------

`httpsdate.py` validates the X.509 certificates of the remote servers.
This effectively authenticates the time information using the X.509 PKI system.
Therefore, a man-in-the-middle attacker can not deliberately set an incorrect time without breaking the TLS connection(s).

The attacker can, however, drop the connections, thus preventing time synchronisation.

Rogue Servers
-------------

By setting the system clock to a value obtained from a remote server, one trusts the remote server's administrator to keep their time correct (and reasonably accurate).

In order to reduce the amount of trust that needs to be put in each remote server, `httpsdate.py` can use multiple servers.
If more than half of the remote servers that provide a usable time also provide a correct time, the use of the median ensures that the selected time is bounded by correct time values.
Therefore, a single rogue server can not influence the resulting system time (as long as at least two other servers respond, that is).

Man-in-the-Middle and Rogue Servers
-----------------------------------

A man-in-the-middle attacker who also controls (at least) one of the queried servers can easily drop connections to the servers they do not control and therefore force a single usable time value.

Using the parameter `--max-failed` provides some protection in this scenario as the acceptable number of failed remote servers - e.g. due to dropped connections - can be limited.
This effectively raises the number of servers that need to be under the control of the attacker.
Still, more than half of the responses need to be correct to ensure that the system clock is set to a correct time.

Software Bugs
-------------

`httpsdate.py` depends on other software.
For instance, is written in python and runs on the Linux kernel.
Bugs in the python interpreter and the Linux kernel may therefore affect `httpsdate.py`.
`httpsdate.py` may have bugs of its own.

For this reason, `httpsdate.py` attempts adhering to the principle of least privilege.
Setting the system clock on Linux requires elevated privileges, but not full `root` privileges.
`httpsdate.py` works well with only the capability `CAP_SYS_TIME`, which is required to set the clock.
If it is started with full `root` privileges, which is often more convenient than employing fine-grained capability control, it drops all unnecessary privileges and runs with the user and group id of an unprivileged user.
This is, of course, done before connecting to the network.

There are, however, further security measures that `httpsdate.py` does not currently employ itself, such as namespaces and seccomp filters.
It should be possible to use `httpsdate.py` together with these technologies, if they are not configured too restrictive.
To run `httpsdate.py` in a restricted sandbox, one can use systemd, bubblewrap or firejail, for instance.

`httpsdate.py` itself is FOSS and fairly short and simple code.
It actually has fewer raw lines than this readme.
The code can be audited independently to increase the confidence that it does not exhibit any undesirable behaviour.

Considerations on Accuracy
==========================

As mentioned earlier, the accuracy of `httpsdate.py` is not very high.
"Not very high" means that is should usually be within a few seconds of the reference time.
This is not ideal, but good enough for most purposes.

There are three factors that influence the accuracy and that can, to some extent, be taken into account in order to get better results.

Resolution
----------

`httpsdate.py` retrieves the remote time from the `Date` HTTP header, which only has a resolution of one second.
Hence, sub-second accuracy is simply not achievable with this approach.

Network Delays
--------------

The time, as set by the remote server, takes some time to reach `httpsdate.py`, which then takes a few more CPU cycles before the system clock is set.
`httpsdate.py` does not do anything clever to correct these delays or even measure the amount of error.
This simply has not been given consideration and likely never will be.
Any attempts may turn out to be infeasible due to the limited resolution of the obtained time data.

The usual methods for reducing network delays apply, e.g. picking servers that have quick response times.

Remote Clock Accuracy
---------------------

The `Date` header is not intended for communicating accurate, current time information.
Therefore, administrators of HTTPS servers may not keep their own clock very accurate.
Moreover, caching (reverse) proxy servers and similar network components may result in stale `Date` headers being returned by remote servers.

While it is possible to use `httpsdate.py` with any modern HTTPS-capable web server, it does make sense to pick servers that are expected to keep their own clocks as accurate as possible and always generate fresh headers.

License
=======

MIT
