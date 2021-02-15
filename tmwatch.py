import contextlib
import plistlib
import shutil
import signal
import subprocess
import threading
from argparse import ArgumentParser
from datetime import timedelta
from collections import namedtuple

from progress.bar import IncrementalBar

TmStatus = namedtuple('TmStatus', ('phase', 'percent', 'etr'))


# Use a threading.Event for interruptible sleep
stop_event = threading.Event()


class TMBar(IncrementalBar):

    # Max width of Time Machine phase string
    phase_width = 24

    # Progress bar width
    width = 32

    def __init__(self):
        super(TMBar, self).__init__(
            message=' ' * self.phase_width,
            max=1,
            suffix='%(percent)5.1f%% ETR %(etr_str)8s',
        )
        self.phase = ''
        self.etr = None

    def set(self, status):
        self._set_phase(status.phase)
        self.etr = status.etr
        if status.percent is not None:
            self.goto(status.percent)
        else:
            self.update()

    def _set_phase(self, phase):
        self.phase = phase
        phase_width = self.phase_width
        if len(phase) > phase_width:
            self.message = phase[:phase_width-1] + '…'
        else:
            self.message = phase.ljust(phase_width)

    @property
    def etr_str(self):
        if self.etr is None:
            return '--:--:--'
        else:
            return timedelta(seconds=self.etr)


def get_tm_status():
    raw_output = subprocess.run(['tmutil', 'status', '-X'],
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,
                                check=True).stdout
    status = plistlib.loads(raw_output)
    phase = status.get('BackupPhase')
    if not phase:
        phase = subprocess.run(['tmutil', 'currentphase'],
                               stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE,
                               text=True,
                               check=True).stdout.strip()
    percent = status.get('Percent')
    if percent is not None and percent < 0:
        percent = 0
    etr = None
    progress = status.get('Progress')
    if progress:
        etr = progress.get('TimeRemaining')
    return TmStatus(
        phase=phase,
        percent=percent,
        etr=etr,
    )


def should_exit(args, status):
    if args.run_indefinitely:
        return False
    return status.phase == 'BackupNotRunning'


def monitor(stack, args):
    bar = bar = stack.enter_context(TMBar()) if args.show_progress else None
    status = get_tm_status()
    display(args, bar, status)

    while not (should_exit(args, status) or stop_event.wait(args.interval)):
        status = get_tm_status()
        display(args, bar, status)


def tput(arg):
    subprocess.run(['tput', arg])


def clear():
    subprocess.run(['clear', '-x'])


def truncate(str, lines, columns):
    str_lines = str.rstrip('\n').splitlines()[:lines]
    return '\n'.join(line[:columns] for line in str_lines)


def display(args, bar, status):
    if args.show_status:
        hr_status = subprocess.run(['tmutil', 'status'],
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,
                                   text=True,
                                   check=True).stdout
        tsize = shutil.get_terminal_size()
        dl = 2 if args.show_progress else 0
        hr_status_trunc = truncate(hr_status, tsize.lines - dl, tsize.columns)
        clear()
        if args.show_progress:
            bar.set(status)
            print('\n\n', hr_status_trunc, sep='', end='', flush=True)
        else:
            print(hr_status_trunc, end='', flush=True)
    elif args.show_progress:
        bar.set(status)


def setup_signal_handling():
    def handler(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handler)


def prepare_term(stack, args):
    if args.show_status:
        # Enable alternate "screen" for displaying status
        tput('smcup')
        stack.callback(tput, 'rmcup')


if __name__ == '__main__':
    parser = ArgumentParser(description='Monitor Time Machine backup progress')
    parser.add_argument('-n', '--interval', type=float, default=2,
                        help="Update interval in seconds")
    parser.add_argument('-i', '--run-indefinitely', action='store_true',
                        help="Don't exit when backup completes")
    parser.add_argument('-s', '--show-status', action='store_true',
                        help="Show tmutil status output")
    parser.add_argument('-P', '--hide-progress',
                        dest='show_progress', action='store_false',
                        help="Disable progress bar")

    args = parser.parse_args()
    if args.run_indefinitely and not (args.show_status or args.show_progress):
        # Doesn't make sense to run indefinitely without displaying anything
        args.show_status = True

    setup_signal_handling()

    with contextlib.ExitStack() as stack:
        prepare_term(stack, args)
        monitor(stack, args)

    if not args.run_indefinitely and stop_event.is_set():
        # Exited due to SIGINT
        exit(130)
