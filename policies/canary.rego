package canary

default allow := false

allow := true if {
    input.error_rate <= 1.0
    input.p99_latency_ms <= 500
}

reason := "Error rate too high (must be <= 1%)" if {
    input.error_rate > 1.0
}

reason := "P99 latency too high (must be <= 500ms)" if {
    input.p99_latency_ms > 500
    input.error_rate <= 1.0
}
