# Log Management and Rotation

**Last Updated:** 2025-11-11
**Status:** Implemented

---

## Overview

Org Archivist implements a dual-layer log rotation strategy to prevent unbounded log file growth and potential storage exhaustion:

1. **Application-level rotation** - Python logging handlers manage application log files
2. **Container-level rotation** - Docker manages container stdout/stderr logs

This approach ensures logs are retained for troubleshooting while automatically cleaning up old logs to prevent disk space issues.

---

## Application-Level Log Rotation

### Configuration

Log rotation settings are configured in `.env` or as environment variables:

```bash
# Logging Configuration
LOG_FILE=./logs/app.log
LOG_LEVEL=INFO

# Rotation Settings
LOG_ROTATION_ENABLED=true           # Enable automatic rotation
LOG_ROTATION_WHEN=midnight          # When to rotate (midnight, H, D, W0-W6)
LOG_ROTATION_INTERVAL=1             # Rotation interval (1 = daily)
LOG_ROTATION_BACKUP_COUNT=30        # Days of logs to retain (30 days)
LOG_MAX_BYTES=10485760              # Max file size before rotation (10MB)
LOG_BACKUP_COUNT=10                 # Number of backup files for size-based rotation
```

### Rotation Strategy

**Time-Based Rotation (Default):**
- Rotates daily at midnight
- Keeps 30 days of historical logs
- Rotated files named: `app.log.2025-11-01`, `app.log.2025-11-02`, etc.

**Rotation Options:**
- `midnight` - Rotate at midnight
- `H` - Rotate every hour
- `D` - Rotate every day
- `W0`-`W6` - Rotate on specific weekday (0=Monday, 6=Sunday)

### Log File Locations

**Development:**
```
./logs/
  ├── app.log              # Current log file
  ├── app.log.2025-11-10   # Yesterday's logs
  ├── app.log.2025-11-09   # 2 days ago
  └── ...                  # Up to 30 days retained
```

**Docker Container:**
```
/app/logs/
  ├── app.log
  ├── app.log.2025-11-10
  └── ...
```

Logs are mounted from the container to the host via Docker volume:
```yaml
volumes:
  - ./logs:/app/logs
```

---

## Container-Level Log Rotation

### Docker Logging Configuration

Docker automatically rotates container stdout/stderr logs to prevent unbounded growth.

**Backend Service:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"      # Max 10MB per log file
    max-file: "5"        # Keep 5 files (50MB total)
    compress: "true"     # Compress rotated logs
```

**Frontend Service:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"      # Max 10MB per log file
    max-file: "3"        # Keep 3 files (30MB total)
    compress: "true"     # Compress rotated logs
```

### Docker Log Locations

Docker stores container logs in:
```
/var/lib/docker/containers/{container-id}/{container-id}-json.log
/var/lib/docker/containers/{container-id}/{container-id}-json.log.1.gz
/var/lib/docker/containers/{container-id}/{container-id}-json.log.2.gz
...
```

---

## Viewing Logs

### Application Logs (File-Based)

**Current logs:**
```bash
# Local development
tail -f logs/app.log

# Inside container
docker exec -it org-archivist-backend tail -f /app/logs/app.log
```

**Historical logs:**
```bash
# View yesterday's logs
cat logs/app.log.2025-11-10

# Search historical logs
grep "ERROR" logs/app.log.*
```

### Container Logs (Docker)

**Current container logs:**
```bash
# Follow backend logs
docker-compose logs -f backend

# Follow all services
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 backend
```

**Filtered logs:**
```bash
# Show only errors
docker-compose logs backend | grep ERROR

# Show logs since specific time
docker-compose logs backend --since="2025-11-11T10:00:00"
```

---

## Log Retention Policy

### Summary

| Log Type | Retention | Max Size | Location |
|----------|-----------|----------|----------|
| Application logs (file) | 30 days | 10MB per file | `./logs/app.log.*` |
| Container logs (backend) | 50MB total | 10MB per file | Docker container logs |
| Container logs (frontend) | 30MB total | 10MB per file | Docker container logs |

### Storage Estimates

**Application logs:**
- Daily log size: ~50-200MB (depends on traffic)
- 30-day retention: ~1.5-6GB maximum

**Container logs:**
- Backend: 50MB maximum (5 files × 10MB)
- Frontend: 30MB maximum (3 files × 10MB)
- Total: ~80MB maximum for container logs

**Total estimated storage:** ~1.6-6.1GB for 30 days of logs

---

## Disabling Log Rotation

### Application-Level

To disable file-based log rotation (not recommended):

```bash
# In .env
LOG_ROTATION_ENABLED=false
```

This will cause logs to write to a single file without rotation, which can lead to unbounded growth.

### Container-Level

Docker log rotation cannot be disabled per-service, but you can increase limits:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "100m"     # Larger file size
    max-file: "10"       # More backup files
```

---

## Troubleshooting

### Issue: No log files created

**Cause:** Log directory doesn't exist or insufficient permissions

**Solution:**
```bash
# Create logs directory
mkdir -p logs
chmod 755 logs

# Check Docker volume mount
docker-compose down
docker-compose up -d
```

### Issue: Old logs not being deleted

**Cause:** `LOG_ROTATION_BACKUP_COUNT` set too high or rotation not working

**Solution:**
```bash
# Check rotation configuration
docker exec org-archivist-backend env | grep LOG_

# Manually clean old logs
find logs -name "app.log.*" -mtime +30 -delete
```

### Issue: Docker logs consuming too much space

**Check Docker log sizes:**
```bash
# Find container ID
docker ps

# Check log file size
ls -lh /var/lib/docker/containers/{container-id}/*.log*
```

**Solution:**
```bash
# Prune old Docker logs (careful - removes stopped containers too)
docker system prune -a

# Or restart with smaller log settings in docker-compose.yml
```

### Issue: Cannot view logs

**Cause:** Logs written to different location or permissions issue

**Solution:**
```bash
# Check log file location in container
docker exec org-archivist-backend ls -la /app/logs/

# Check host mount
ls -la logs/

# View logs from different source
docker-compose logs backend
```

---

## Production Recommendations

### For Small to Medium Deployments

Current configuration is appropriate:
- 30 days retention
- Daily rotation
- 10MB max file size

### For Large Deployments

Consider centralized logging:

**Option 1: ELK Stack (Elasticsearch, Logstash, Kibana)**
```yaml
logging:
  driver: "gelf"
  options:
    gelf-address: "udp://logstash:12201"
```

**Option 2: Loki + Grafana**
```yaml
logging:
  driver: "loki"
  options:
    loki-url: "http://loki:3100/loki/api/v1/push"
```

**Option 3: Cloud Logging**
- AWS CloudWatch
- Google Cloud Logging
- Azure Monitor

### For Compliance Requirements

If you need to retain logs for compliance (e.g., SOC2, HIPAA):

1. **Increase retention period:**
   ```bash
   LOG_ROTATION_BACKUP_COUNT=365  # 1 year
   ```

2. **Archive to S3/Cloud Storage:**
   ```bash
   # Daily cron job to archive logs
   0 0 * * * tar -czf logs-$(date +\%Y-\%m-\%d).tar.gz logs/*.log.* && \
             aws s3 cp logs-$(date +\%Y-\%m-\%d).tar.gz s3://my-logs-bucket/
   ```

3. **Enable audit logging:**
   - All log access is already tracked via audit middleware
   - See `backend/app/middleware/audit.py`

---

## Monitoring Log Health

### Automated Monitoring

Add to monitoring/alerting system:

```bash
# Alert if log file exceeds 100MB (rotation may have failed)
LOG_SIZE=$(du -m logs/app.log | cut -f1)
if [ $LOG_SIZE -gt 100 ]; then
  echo "WARNING: Log file exceeds 100MB, rotation may have failed"
fi

# Alert if logs directory exceeds 10GB
DIR_SIZE=$(du -sm logs | cut -f1)
if [ $DIR_SIZE -gt 10240 ]; then
  echo "WARNING: Logs directory exceeds 10GB"
fi
```

### Manual Health Check

```bash
# Check current log file size
ls -lh logs/app.log

# Check total logs directory size
du -sh logs/

# Count backup files
ls -1 logs/app.log.* | wc -l

# Check Docker container log sizes
docker ps -q | xargs docker inspect --format='{{.LogPath}}' | xargs du -h
```

---

## See Also

- [Application Configuration](../backend/app/config.py) - Full configuration options
- [Docker Compose Configuration](../docker-compose.yml) - Container logging settings
- [Audit Logging](../backend/app/middleware/audit.py) - Audit trail logging
