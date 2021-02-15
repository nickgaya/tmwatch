# tmwatch

A command-line utility to monitor Time Machine backup progress on Mac OS.

## Usage

To monitor an ongoing time machine backup:

    python3 tmwatch.py

By default, the script will query time machine status every 2s and display a
progress bar until the backup is complete.

Supported options:

* `-n`/`--interval`: Set the update interval in seconds.

* `-i`/`--run-indefinitely`: Don't exit on backup completion; keep monitoring
  status until interrupted.

* `-s`/`--show-status`: Display the full output from `tmutil status`.

* `-P`, `--hide-progress`: Disable the progress bar. This can be used to
  non-interactively wait for a Time Machine backup to complete.
