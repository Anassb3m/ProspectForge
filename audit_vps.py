import pexpect
import sys

print("Connecting to VPS to audit disk usage...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== DISK USAGE ==="
df -h /
echo ""
echo "=== DOCKER SYSTEM USAGE ==="
docker system df
echo ""
echo "=== LARGEST DIRECTORIES IN /opt ==="
du -sh /opt/* 2>/dev/null | sort -rh
echo ""
echo "=== LARGEST DOCKER VOLUMES ==="
du -sh /var/lib/docker/volumes/* 2>/dev/null | sort -rh | head -n 10
echo ""
echo "=== LARGEST DOCKER CONTAINERS (LOGS/DIFFS) ==="
du -sh /var/lib/docker/containers/* 2>/dev/null | sort -rh | head -n 10
echo ""
echo "=== SYSTEMD JOURNAL USAGE ==="
journalctl --disk-usage
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
