import plistlib
import subprocess
import time
from datetime import timedelta

from progress.bar import IncrementalBar

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

    def set(self, phase, percent=None, etr=None):
        self._set_phase(phase)
        self.etr = etr
        if percent is not None:
            self.goto(percent)
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
    return {
        'phase': phase,
        'percent': percent,
        'etr': etr,
    }

if __name__ == '__main__':
    bar = TMBar()
    bar.start()
    bar.set(**get_tm_status())
    while bar.phase != 'BackupNotRunning':
        time.sleep(2)
        bar.set(**get_tm_status())
    bar.finish()
