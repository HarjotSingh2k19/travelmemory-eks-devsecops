# THIS FILE IS SAME AS main.tf in other projects 

# data means "look up something that exists, don't create it".
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical's official AWS account ID

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "bastion" {
  name        = "${var.cluster_name}-bastion-sg"
  description = "SSH access restricted to home IP"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from home IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.my_home_ip}/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # this allows all outbound traffic from the bastion, unrestricted (with protocol -1 and cidr = 0.0.0.0/0).
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.cluster_name}-bastion-sg" }
}

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public[0].id
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.bastion.id]

  tags = { Name = "${var.cluster_name}-bastion" }
}