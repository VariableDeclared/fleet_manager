terraform {
  required_providers {
    lxd = {
      source  = "terraform-lxd/lxd"
      version = "~> 2.0"
    }
  }
}
provider "lxd" {
  generate_client_certificates = true
  accept_remote_certificate    = true
}
resource "lxd_profile" "fleet_agent_profile" {
  name = "fleet-agent-bootstrap"
  config = {
    "user.user-data" = file("${path.module}/cloud-init.yaml")
  }

}
resource "lxd_instance" "ubuntu_target" {
  name      = "fleet-ubuntu-01"
  image     = "ubuntu:22.04"
  type      = "virtual-machine"
  profiles  = ["default", lxd_profile.fleet_agent_profile.name]
  device {
    name = "eth0"
    type = "nic"
    properties = {
      nictype = "bridged"
      parent = "br0"
    }
  }
}
