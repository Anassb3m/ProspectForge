import pexpect
import sys

print("Connecting to VPS to check database...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
systemctl status mysql mariadb postgresql --no-pager
'"""

child = pexpect.spawn(command, encoding='utf-8')
child.logfile = sys.stdout

while True:
    index = child.expect(['Enter passphrase for key', 'password:', pexpect.EOF, pexpect.TIMEOUT], timeout=60)
    if index == 0:
        child.sendline('Anass20121971@')
    elif index == 1:
        child.sendline('Anass20121971@')
    elif index == 2:
        break
    elif index == 3:
        break

print("Exit status:", child.exitstatus)
