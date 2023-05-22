# Ping Hosts and URLs and keep stats on successes and failures

Run this as a daemon on your box and check in to see if there are problems.

Intended to be a slightly different approach to blackbox_exporter.

## Installing

```sh
pip install pingertron
```

## Running

```sh
pingertron probes.yaml
```

ICMP usually needs root access to send packets:

```sh
sudo pingertron probes.yaml
```

There is an example [probes.yaml](examples/probes.yaml) you can use as a basis for your own.

## probes.yaml

Specify one or more probes to run using probes.yaml.

This file is re-read on each evaluation cycle, so you can update it without restarting the process.

Example probes.yaml:

```yaml
interval_seconds: 60  # seconds between each batch of probes being sent

probes:
- protocol: http  # one of icmp or http
  description: my probe  # optional description
  # probe specific properties
# HTTP Probe
- protocol: http
  # description: my HTTP probe  # optional description
  url: https://example.com/  # URL to probe, http or https
  method: GET  # HTTP method to use
  expected_status_code: 200  # HTTP status code you expect, usually 200
# ICMP Probe
- protocol: icmp
  # description: my ICMP probe  # optional description
  hostname: 10.0.0.1  # Hostname or IP to ping.
```

The canonical definition of what goes into this file can be found in [probes_config.py](pingertron/probes_config.py).

## Developing

### devenv

If you use [devenv](https://devenv.sh):

```sh
direnv allow .
```

### poetry

If you use [poetry](https://python-poetry.org):

```sh
poetry install
poetry run pingertron
```
