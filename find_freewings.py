import pexpect
import sys

print("Connecting to VPS to find freewings...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== FINDING FREEWINGS ==="
find / -maxdepth 3 -type d -iname "*freewings*" 2>/dev/null
echo "=== FINDING DOCKER COMPOSE FILES ==="
find /opt -name "docker-compose*.yml" -print0 | xargs -0 grep -il freewings 2>/dev/null
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
