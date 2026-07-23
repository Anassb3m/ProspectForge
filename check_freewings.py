import pexpect
import sys

print("Connecting to VPS to investigate freewings...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== DOCKER COMPOSE FILES ==="
find /opt -name "docker-compose*.yml" 2>/dev/null | grep -i freewings

echo "=== WHAT IS ON PORT 19080 ==="
netstat -nlpt | grep 19080

echo "=== CHECKING RUNNING CONTAINERS FOR FREEWINGS ==="
docker ps | grep freewings
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
