# Fix all joins in metrics.py
import re

with open('metrics.py', 'r') as f:
    content = f.read()

# Fix the ml_classifications join - should use a.id not a.alert_id
content = content.replace(
    'LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.alert_id',
    'LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.id::text'
)

# action_logs join is already correct (al.alert_id is UUID, a.id is UUID)
# But let's remove the cast since they're both UUID
content = content.replace(
    'LEFT JOIN audit.action_logs al ON al.alert_id::uuid = a.id::uuid',
    'LEFT JOIN audit.action_logs al ON al.alert_id = a.id'
)

with open('metrics.py', 'w') as f:
    f.write(content)

print('Fixed metrics.py joins')
