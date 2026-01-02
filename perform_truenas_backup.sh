#!/usr/bin/expect

# Increase timeout for initial connection
set timeout 30
spawn ssh -o StrictHostKeyChecking=no olindo@10.10.10.50

expect {
    "password:" { send "Compli61!\r"; exp_continue }
    "olindo@truenas" { send "sudo -s\r" }
    timeout { puts "SSH Timeout"; exit 1 }
}

expect {
    "password" { send "Compli61!\r" }
    "root@truenas" { }
    "#" { }
    timeout { puts "Sudo Timeout"; exit 1 }
}

# Verify root
expect "#"
send "whoami\r"
expect "root"

# Debug filesystem status
send "echo 'Filesystem Status Check:'\r"
send "zfs get readonly oliraid/backup-stripe\r"
expect "#"

# Disable readonly if it is on (User asked to force/fix/sudo it)
# We try to force it off just in case
send "zfs set readonly=off oliraid/backup-stripe\r"
expect "#"

set timeout -1
send "echo 'Creating directory...'\r"
send "mkdir -p /mnt/oliraid/backup-stripe/mig-backup\r"
expect "#"

send "echo 'Starting Copy...'\r"
send "if \[ -d \"/mnt/stripe/k8s-arr\" \]; then cp -a /mnt/stripe/k8s-arr/* /mnt/oliraid/backup-stripe/mig-backup/; else echo 'Source not found'; fi\r"
expect "#"

send "echo 'DONE. Check size:'\r"
send "du -sh /mnt/oliraid/backup-stripe/mig-backup\r"
expect "#"

send "exit\r"
expect eof
