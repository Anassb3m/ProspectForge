import pexpect
import sys

print("Connecting to VPS to run deploy script...")
child = pexpect.spawn("ssh -o StrictHostKeyChecking=no root@76.13.52.38 'cd /opt/prospectforge && git fetch origin && git checkout antigravity/prospectforge-level-300 && git pull origin antigravity/prospectforge-level-300 && DEPLOY_BRANCH=antigravity/prospectforge-level-300 ./scripts/vps-update.sh'", encoding='utf-8')
child.logfile = sys.stdout

while True:
    index = child.expect(['Enter passphrase for key', 'password:', pexpect.EOF, pexpect.TIMEOUT], timeout=600)
    if index == 0:
        child.sendline('Anass20121971@')
    elif index == 1:
        child.sendline('Anass20121971@')
    elif index == 2:
        break
    elif index == 3:
        break

print("Exit status:", child.exitstatus)
