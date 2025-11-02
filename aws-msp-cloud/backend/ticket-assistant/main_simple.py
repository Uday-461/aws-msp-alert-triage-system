# Simplified version - comment out incident endpoints for now
import sys
with open('/home/ec2-user/aws-msp-cloud/backend/ticket-assistant/main.py', 'r') as f:
    lines = f.readlines()

with open('/home/ec2-user/aws-msp-cloud/backend/ticket-assistant/main_working.py', 'w') as f:
    skip_until = None
    for i, line in enumerate(lines):
        # Comment out incident endpoints
        if '@app.get("/incidents"' in line:
            f.write('# TEMPORARILY DISABLED\n')
            f.write('# ' + line)
            skip_until = 'except Exception'
        elif skip_until and skip_until in line:
            f.write('# ' + line)
            skip_until = None
        elif skip_until:
            f.write('# ' + line)
        elif '@app.post("/detect-incidents"' in line:
            f.write('# TEMPORARILY DISABLED\n')
            f.write('# ' + line)
            skip_until = 'except Exception'
        else:
            f.write(line)

print('Created simplified version')
