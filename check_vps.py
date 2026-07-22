import pexpect
import sys

child = pexpect.spawn("ssh -o StrictHostKeyChecking=no root@76.13.52.38 'cd /opt/prospectforge && git log -1 && echo \"--DOCKER PS--\" && docker ps'", encoding='utf-8')
child.logfile = sys.stdout

while True:
    index = child.expect(['Enter passphrase for key', 'password:', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
    if index == 0:
        child.sendline('Anass20121971@')
    elif index == 1:
        child.sendline('Anass20121971@')
    elif index == 2:
        break
    elif index == 3:
        break
