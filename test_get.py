import pexpect
import sys

print("Connecting to VPS to test GET requests fully...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== PORTFOLIO ==="
curl -k -v -s https://anass.elevya.tech | grep -i title
echo ""

echo "=== PROSPECT FORGE ==="
curl -k -v -s -H "Accept: text/html" https://prospect.elevya.tech | head -n 20
echo ""

echo "=== FREEWINGS ==="
curl -k -v -s https://freewings.elevya.tech | head -n 10
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
