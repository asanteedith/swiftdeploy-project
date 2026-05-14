package infra

default allow := false

allow := true if {
    input.disk_free_gb >= 10
    input.cpu_load <= 2.0
}

reason := "Disk space too low (must be >= 10GB)" if {
    input.disk_free_gb < 10
}

reason := "CPU load too high (must be <= 2.0)" if {
    input.cpu_load > 2.0
    input.disk_free_gb >= 10
}
