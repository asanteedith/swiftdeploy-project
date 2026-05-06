package infra

# By default, we don't allow unless conditions are met
default allow = false

# Allow only if BOTH conditions are true
allow {
    input.disk_free >= input.thresholds.disk_min
    input.cpu_load <= input.thresholds.cpu_max
}

# Provide the reason if it's NOT allowed
reason = "Disk below 10GB" {
    input.disk_free < input.thresholds.disk_min
}

reason = "CPU load above 2.0" {
    input.cpu_load > input.thresholds.cpu_max
}

# Fallback reason
default reason = "Infrastructure health check failed"