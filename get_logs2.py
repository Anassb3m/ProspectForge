import pexpect
import sys

print("Connecting to VPS to get logs...")
child = pexpect.spawn("ssh -o StrictHostKeyChecking=no root@76.13.52.38 'docker logs --tail 100 prospectforge_prod-app-1'", encoding='utf-8')
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

print("Exit status:", child.exitstatus)
