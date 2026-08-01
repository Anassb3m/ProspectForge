import pexpect
import sys

print("Connecting to VPS to start scheduler...")
# We use sed to change scheduler flags to true, then start celery-beat.
child = pexpect.spawn("ssh -o StrictHostKeyChecking=no root@76.13.52.38 'cd /opt/prospectforge && sed -i \"s/ENABLE_SCHEDULER=false/ENABLE_SCHEDULER=true/g\" .env && sed -i \"s/ENABLE_NIGHTLY_INGESTION=false/ENABLE_NIGHTLY_INGESTION=true/g\" .env && sed -i \"s/ENABLE_NIGHTLY_CONTACT_DISCOVERY=false/ENABLE_NIGHTLY_CONTACT_DISCOVERY=true/g\" .env && sed -i \"s/ENABLE_SCORE_RECONCILIATION=false/ENABLE_SCORE_RECONCILIATION=true/g\" .env && docker compose --profile scheduler up -d celery-beat && docker compose restart celery-beat'", encoding='utf-8')
child.logfile = sys.stdout

while True:
    index = child.expect(['Enter passphrase for key', 'password:', pexpect.EOF, pexpect.TIMEOUT], timeout=120)
    if index == 0:
        child.sendline('Anass20121971@')
    elif index == 1:
        child.sendline('Anass20121971@')
    elif index == 2:
        break
    elif index == 3:
        break

print("Exit status:", child.exitstatus)
