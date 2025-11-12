# API Rate Limiting

**Version:** 1.0
**Last Updated:** 2025-11-11
**Status:** Implemented

---

## Overview

The Org Archivist API implements rate limiting to protect against abuse, prevent DoS attacks, and control operational costs. Rate limiting is applied at the middleware level using `aiolimiter` for async request throttling.

### Key Features

- **IP-based limiting**: For unauthenticated endpoints (login, register)
- **User-based limiting**: For authenticated endpoints (queries, documents)
- **Endpoint-specific limits**: Different limits for different operation types
- **Graceful degradation**: Clear error messages with retry guidance
- **Configurable**: Can be enabled/disabled via environment variables

---

## Rate Limit Tiers

### Authentication Endpoints (IP-based)

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `POST /api/auth/login` | 5 requests | 60 seconds | Prevent brute force attacks |
| `POST /api/auth/register` | 3 requests | 1 hour | Prevent spam account creation |
| `POST /api/auth/refresh` | 10 requests | 60 seconds | Allow token refresh without abuse |

### Generation Endpoints (User-based)

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `POST /api/query` | 10 requests | 60 seconds | Control Claude API costs |
| `POST /api/query/stream` | 10 requests | 60 seconds | Control Claude API costs |
| `POST /api/chat` | 10 requests | 60 seconds | Control Claude API costs |
| `POST /api/chat/stream` | 10 requests | 60 seconds | Control Claude API costs |

### Document Operations (User-based)

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `POST /api/documents/upload` | 10 requests | 60 seconds | Prevent resource exhaustion |
| `DELETE /api/documents/{id}` | 20 requests | 60 seconds | Allow batch operations |
| `GET /api/documents` | 100 requests | 60 seconds | Generous for read operations |

### Read Endpoints (User-based)

| Endpoint Pattern | Limit | Window | Rationale |
|------------------|-------|--------|-----------|
| `GET /api/writing-styles` | 100 requests | 60 seconds | Generous for read operations |
| `GET /api/prompts` | 100 requests | 60 seconds | Generous for read operations |
| `GET /api/outputs` | 100 requests | 60 seconds | Generous for read operations |

### System Endpoints (IP-based)

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `GET /api/health` | 60 requests | 60 seconds | Allow monitoring tools |
| `GET /api/metrics` | 60 requests | 60 seconds | Allow monitoring tools |

### Default (User-based)

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| All other authenticated endpoints | 30 requests | 60 seconds | Reasonable default |

---

## Client Identification

### Unauthenticated Requests

Rate limiting uses **IP address** with the following priority:

1. `X-Forwarded-For` header (first IP if multiple)
2. `X-Real-IP` header
3. Direct client IP from socket

### Authenticated Requests

Rate limiting uses **User ID** from the authenticated session.

This allows:
- More granular control per user
- Higher limits for authenticated users
- User-specific rate limit enforcement

---

## Response Headers

All API responses include rate limit information:

```http
X-RateLimit-Limit: 10
X-RateLimit-Window: 60s
X-RateLimit-Type: user
```

### When Rate Limit is Exceeded

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 5
X-RateLimit-Window: 60s
X-RateLimit-Type: ip

{
  "error": "Rate limit exceeded",
  "detail": "Maximum 5 requests per 60 seconds. Please try again in 60 seconds.",
  "retry_after": 60,
  "limit": 5,
  "window": "60s"
}
```

---

## Configuration

### Environment Variables

```bash
# Enable or disable rate limiting
ENABLE_RATE_LIMITING=true

# Cleanup interval for stale rate limiters (in hours)
RATE_LIMIT_CLEANUP_INTERVAL_HOURS=1
```

### Disabling Rate Limiting

For development or testing, rate limiting can be disabled:

```bash
# In .env file
ENABLE_RATE_LIMITING=false
```

**Warning**: Never disable rate limiting in production!

---

## Implementation Details

### Architecture

```
Request → RateLimitMiddleware → Check IP/User → Get Limiter → Check Limit
                ↓                                                   ↓
            Proceed                                           429 Response
```

### Technology Stack

- **Library**: `aiolimiter` - Async rate limiting for FastAPI
- **Storage**: In-memory (per-instance)
- **Cleanup**: Automatic removal of stale limiters after 1 hour

### Middleware Order

Rate limiting middleware is executed **first** to reject requests early:

```python
app.add_middleware(RateLimitMiddleware)  # First - reject early
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(MetricsMiddleware)
```

### Performance Characteristics

- **Memory Usage**: ~1KB per active client
- **Latency Overhead**: <1ms per request
- **Cleanup**: Automatic hourly cleanup of stale limiters

---

## Error Handling

### Client Response

When rate limit is exceeded, clients receive:

1. **HTTP 429** status code
2. **Retry-After** header (seconds to wait)
3. **Error details** in JSON body
4. **Rate limit metadata** in headers

### Example Error Response

```json
{
  "error": "Rate limit exceeded",
  "detail": "Maximum 5 requests per 60 seconds. Please try again in 60 seconds.",
  "retry_after": 60,
  "limit": 5,
  "window": "60s"
}
```

### Recommended Client Handling

```javascript
async function makeRequest(url, options) {
  try {
    const response = await fetch(url, options);

    if (response.status === 429) {
      const data = await response.json();
      const retryAfter = data.retry_after || 60;

      console.log(`Rate limited. Retry in ${retryAfter} seconds`);

      // Wait and retry
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      return makeRequest(url, options);
    }

    return response;
  } catch (error) {
    console.error('Request failed:', error);
    throw error;
  }
}
```

---

## Monitoring & Observability

### Logs

Rate limit events are logged:

```
WARNING - Rate limit exceeded for ip:192.168.1.100 on POST /api/auth/login
INFO - Cleaned up 15 stale rate limiters
```

### Metrics

Track rate limiting effectiveness:

- Total requests blocked
- Rate limit hits by endpoint
- Top rate-limited IPs/users

---

## Security Considerations

### Bypass Prevention

- Rate limits cannot be bypassed by changing user agent
- IP spoofing is mitigated by trusting proxy headers only from known proxies
- Authentication tokens are validated before user-based limiting

### DDoS Protection

While rate limiting helps prevent abuse, it's not a complete DDoS solution:

- **Complementary measures needed**:
  - Infrastructure-level DDoS protection (CloudFlare, AWS Shield)
  - Reverse proxy rate limiting (nginx)
  - Connection limits at load balancer

### Limitations

- **Per-instance**: Rate limits are per application instance (not shared across multiple servers)
- **In-memory**: Limits reset on application restart
- **No persistence**: Rate limit state is not stored in database

---

## Future Enhancements

### Planned Improvements

1. **Redis-backed storage**: Share rate limits across multiple instances
2. **Sliding window**: More precise rate limiting algorithm
3. **Dynamic limits**: Adjust limits based on user tier/plan
4. **Rate limit API**: Allow admins to adjust limits via API
5. **Whitelist/Blacklist**: Exempt specific IPs or users

### Alternative Implementations

For production deployments, consider:

- **nginx rate limiting**: Infrastructure-level, faster, shared across instances
- **CloudFlare rate limiting**: CDN-level, global enforcement
- **Redis-based limiting**: Distributed, persistent, shared state

---

## Testing

### Unit Tests

Run rate limiting tests:

```bash
pytest backend/tests/test_rate_limiting.py -v
```

### Manual Testing

Test rate limit with curl:

```bash
# Make rapid requests to trigger rate limit
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}' \
    -w "\nStatus: %{http_code}\n"
done
```

---

## Troubleshooting

### Common Issues

**Problem**: Rate limit triggered unexpectedly

- **Check**: Multiple clients behind same NAT/proxy share IP
- **Solution**: Implement user-based limiting, authenticate requests

**Problem**: Rate limits not enforced

- **Check**: `ENABLE_RATE_LIMITING` environment variable
- **Solution**: Ensure set to `true` in production

**Problem**: Rate limits too strict/lenient

- **Check**: `RateLimitConfig` values in `backend/app/middleware/rate_limit.py`
- **Solution**: Adjust limits based on usage patterns

---

## References

- **aiolimiter documentation**: https://github.com/mjpieters/aiolimiter
- **FastAPI middleware**: https://fastapi.tiangolo.com/advanced/middleware/
- **HTTP 429 specification**: https://tools.ietf.org/html/rfc6585#section-4

---

## Changelog

### v1.0 (2025-11-11)

- Initial implementation with IP and user-based limiting
- Endpoint-specific rate limits
- Automatic cleanup of stale limiters
- Configuration via environment variables
- Comprehensive test suite
