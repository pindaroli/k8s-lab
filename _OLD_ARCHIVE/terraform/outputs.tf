output "control_plane_ips" {
  value = {
    for k, v in var.control_plane_nodes : k => v.ip
  }
}

output "worker_ips" {
  value = {
    for k, v in var.worker_nodes : k => v.ip
  }
}
