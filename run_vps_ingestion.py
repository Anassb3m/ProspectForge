import pexpect
import sys

print("Connecting to VPS to run ingestion...")
cmd = "ssh -o StrictHostKeyChecking=no root@76.13.52.38 'cd /opt/prospectforge && docker compose exec -T app python -m app.jobs.ingestion --play-code FIELD_OPERATIONS_FR_V2 --mode registry --max-companies 2000 --skip-sirene'"
child = pexpect.spawn(cmd, encoding='utf-8', timeout=600)
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
