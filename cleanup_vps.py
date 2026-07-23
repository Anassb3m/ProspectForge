import pexpect
import sys

print("Connecting to VPS to perform cleanup...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== INITIAL DISK USAGE ==="
df -h /
echo ""

echo "=== DELETING OLD ARCHIVES ==="
rm -f /opt/signal_intel_pre_git_cleanup_20260710T021208Z.tgz
rm -f /opt/signal_intel_current_sanitized_20260706.tar.gz
echo "Archives deleted."
echo ""

echo "=== PRUNING DOCKER BUILD CACHE ==="
docker builder prune -a -f
echo ""

echo "=== PRUNING OLD DOCKER IMAGES ==="
docker image prune -a -f
echo ""

echo "=== FINAL DISK USAGE ==="
df -h /
'"""

child = pexpect.spawn(command, encoding='utf-8')
child.logfile = sys.stdout

while True:
    index = child.expect(['Enter passphrase for key', 'password:', pexpect.EOF, pexpect.TIMEOUT], timeout=3600)
    if index == 0:
        child.sendline('Anass20121971@')
    elif index == 1:
        child.sendline('Anass20121971@')
    elif index == 2:
        break
    elif index == 3:
        break

print("Exit status:", child.exitstatus)
