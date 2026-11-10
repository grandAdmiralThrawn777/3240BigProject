"""Small console adapter for Renode. No Robot, shell or GUI dependency."""
import queue
import subprocess
import threading
from pathlib import Path


class Renode:
    def __init__(self, executable, log):
        self.log = Path(log).open('w', encoding='utf-8')
        self.lines = queue.Queue()
        self.sequence = 0
        self.process = subprocess.Popen([str(executable), '--disable-gui', '--console', '--plain'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', bufsize=1)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.command('echo "SESSION_READY"')
        self.command('logLevel 2')

    def _read(self):
        for line in self.process.stdout:
            self.log.write(line)
            self.log.flush()
            self.lines.put(line)
        self.lines.put(None)

    def command(self, command, timeout=30):
        self.sequence += 1
        marker = 'TANK_END_' + str(self.sequence)
        self.process.stdin.write(command + '\necho "' + marker + '"\n')
        self.process.stdin.flush()
        result = []
        while True:
            line = self.lines.get(timeout=timeout)
            if line is None:
                raise RuntimeError('Renode exited during command: ' + command)
            # Echoed input contains quotes; the echo result is a bare marker.
            if line.strip() == marker:
                break
            result.append(line)
        output = ''.join(result)
        if 'There was an error' in output or '[ERROR]' in output or '[FATAL]' in output:
            raise RuntimeError(output)
        return output

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.write('quit\n')
                self.process.stdin.flush()
                self.process.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait()
        self.reader.join(timeout=2)
        self.log.close()
