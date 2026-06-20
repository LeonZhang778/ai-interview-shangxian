import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('8.166.120.119', username='root', password='5408854088Ab@')

# Copy SQL file to postgres container and run it
cmds = [
    'docker cp /home/deploy/ai-interview/ai-interview-backend/migrations/create_experiences_tables.sql ai-interview-postgres:/tmp/create_exp.sql',
    'docker exec ai-interview-postgres psql -U postgres -d postgres -f /tmp/create_exp.sql',
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print(err)

# Verify
stdin, stdout, stderr = ssh.exec_command('docker exec ai-interview-postgres psql -U postgres -d postgres -c "\\dt"')
print(stdout.read().decode())

ssh.close()
