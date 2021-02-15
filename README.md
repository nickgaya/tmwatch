# tmwatch

A command-line utility to monitor Time Machine backup progress on Mac OS.

## Usage

To monitor an ongoing time machine backup:

    python3 tmwatch.py

The command will query the time machine status every 2s and display a progress
bar until the backup is complete.
