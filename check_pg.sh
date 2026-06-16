#!/bin/bash
export PGPASSWORD=123456
psql -h localhost -U postgres -c "\\du" 2>&1
echo "---"
psql -h localhost -U postgres -c "\\l" 2>&1
