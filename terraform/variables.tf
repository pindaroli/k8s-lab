variable "proxmox_api_url" {
  type = string
  default = "https://192.168.1.125:8006/api2/json"
}

variable "proxmox_api_token_id" {
  type = string
  sensitive = true
}

variable "proxmox_api_token_secret" {
  type = string
  sensitive = true
}

variable "talos_version" {
  type = string
  default = "v1.9.0" # Latest stable as of late 2024/early 2025
}

variable "cluster_name" {
  type = string
  default = "talos-cluster"
}

variable "control_plane_nodes" {
  description = "Configuration for control plane nodes"
  type = map(object({
    node_name = string
    target_node = string
    vmid = number
    cores = number
    memory = number
    disk_size = number
    ip = string
  }))
  default = {
    cp1 = {
      node_name = "talos-cp-1"
      target_node = "pve"
      vmid = 8001
      cores = 2
      memory = 4096
      disk_size = 20
      ip = "192.168.1.201"
    }
    cp2 = {
      node_name = "talos-cp-2"
      target_node = "pve2"
      vmid = 8002
      cores = 2
      memory = 4096
      disk_size = 20
      ip = "192.168.1.202"
    }
    cp3 = {
      node_name = "talos-cp-3"
      target_node = "pve3"
      vmid = 8003
      cores = 2
      memory = 4096
      disk_size = 20
      ip = "192.168.1.203"
    }
  }
}

variable "worker_nodes" {
  description = "Configuration for worker nodes"
  type = map(object({
    node_name = string
    target_node = string
    vmid = number
    cores = number
    memory = number
    disk_size = number
    ip = string
  }))
  default = {
    worker1 = {
      node_name = "talos-worker-1"
      target_node = "pve"
      vmid = 8101
      cores = 8
      memory = 32768
      disk_size = 40
      ip = "192.168.1.211"
    }
    worker2 = {
      node_name = "talos-worker-2"
      target_node = "pve2"
      vmid = 8102
      cores = 3
      memory = 10240
      disk_size = 40
      ip = "192.168.1.212"
    }
  }
}

variable "iso_storage" {
  type = string
  default = "local"
}

variable "vm_storage" {
  type = string
  default = "local-zfs"
}
