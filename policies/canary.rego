package canary

default allow = false

# Allow only if performance is within limits
allow {
    input.error_rate <= input.thresholds.max_error
    input.p99_latency <= input.thresholds.max_latency
}

# Specific reasons for failure
reason = "Error rate too high" {
    input.error_rate > input.thresholds.max_error
}

reason = "Latency too high" {
    input.p99_latency > input.thresholds.max_latency
}

default reason = "Canary health check failed"