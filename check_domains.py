import pexpect
import sys

print("Connecting to VPS to curl systems...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== PORTFOLIO ==="
curl -k -I -m 5 https://anass.elevya.tech
echo ""

echo "=== PROSPECT FORGE ==="
curl -k -I -m 5 https://prospect.elevya.tech
echo ""

echo "=== SIGNAL INTEL FRONTEND ==="
curl -k -I -m 5 https://signal.elevya.tech  # Or whatever it is... let us try the public IP
echo ""

echo "=== LOCAL BUSINESS DATA (FREEWINGS) ==="
curl -k -I -m 5 https://freewings.elevya.tech
echo ""

echo "=== LOCAL BUSINESS DATA (DATA) ==="
curl -k -I -m 5 https://data.elevya.tech
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
