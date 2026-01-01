resource "proxmox_virtual_environment_vm" "talos_worker" {
  for_each = var.worker_nodes

  name      = each.value.node_name
  node_name = each.value.target_node
  vm_id     = each.value.vmid

  cpu {
    cores = each.value.cores
    type  = "host"
  }

  memory {
    dedicated = each.value.memory
  }

  disk {
    datastore_id = var.vm_storage
    file_format  = "raw"
    interface    = "virtio0"
    size         = each.value.disk_size
    ssd          = true
  }

  initialization {
    datastore_id = var.vm_storage
    interface    = "ide0"
    ip_config {
      ipv4 {
        address = "${each.value.ip}/24"
        gateway = "192.168.1.1"
      }
    }
  }

  agent {
    enabled = false
  }

  # Boot order: CD-ROM (ide2), then Disk (virtio0), then Network (net0)
  boot_order = ["ide2", "virtio0", "net0"]

  cdrom {
    file_id = "${var.iso_storage}:iso/talos-${var.talos_version}-metal-amd64.iso"
  }

  network_device {
    bridge = "vmbr0"
    model  = "virtio"
  }

  operating_system {
    type = "l26"
  }

}
