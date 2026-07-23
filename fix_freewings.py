import pexpect
import sys

print("Connecting to VPS to fix Laravel storage permissions and clear cache...")
command = """ssh -o StrictHostKeyChecking=no root@76.13.52.38 '
echo "=== FIXING PERMISSIONS ==="
chown -R www-data:www-data /var/www/freewings/current/storage
chmod -R 775 /var/www/freewings/current/storage

echo "=== CLEARING LARAVEL CACHE PROPERLY ==="
cd /var/www/freewings/current
php artisan cache:clear
php artisan config:clear
php artisan route:clear
php artisan view:clear

echo "=== TESTING API ==="
curl -k -s -v -H "Accept: application/json" https://freewings.elevya.tech/api/destinations | head -n 20
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
