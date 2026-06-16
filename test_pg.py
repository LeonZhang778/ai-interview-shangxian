import subprocess
import os

# Try connecting to postgres using the POSTGRES_USER from env
# The init user is baked into the data volume
os.environ['PGPASSWORD'] = '123456'
result = subprocess.run(
    ['docker', 'exec', 'ai-interview-postgres', 'psql', '-U', 'postgres', '-c', '\\du'],
    capture_output=True, text=True
)
print("postgres/123456:", result.stdout, result.stderr)

# Try without password
result = subprocess.run(
    ['docker', 'exec', 'ai-interview-postgres', 'psql', '-U', 'postgres', '-h', 'localhost', '-c', '\\du'],
    capture_output=True, text=True
)
print("postgres/no-pass:", result.stdout, result.stderr)
