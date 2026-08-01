import pexpect
import sys

print("Connecting to VPS to fix .env and restart...")
# We use sed to change INGESTION_RUN_CONTACTS to false, then start the app.
child = pexpect.spawn("ssh -o StrictHostKeyChecking=no root@76.13.52.38 'cd /opt/prospectforge && sed -i \"s/INGESTION_RUN_CONTACTS=true/INGESTION_RUN_CONTACTS=false/g\" .env && ./scripts/deploy.sh'", encoding='utf-8')
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
