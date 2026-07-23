import pexpect
import sys

print("Connecting to VPS to check freewings JS assets...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== FETCHING HTML ==="
curl -k -s https://freewings.elevya.tech | grep "<script"
echo "=== CHECKING IF JS EXISTS ==="
ls -la /var/www/freewings_webroot/assets/ || ls -la /var/www/freewings/current/public/assets/ || echo "NO ASSETS FOLDER"
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
