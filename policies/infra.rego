package infra

default allow := false

allow := true if {
    input.disk_free_gb >= 10
    input.cpu_load <= 2.0
}

reason := "Disk space too low" if {
    input.disk_free_gb < 10
}

reason := "CPU load too high" if {
    input.cpu_load > 2.0
}
