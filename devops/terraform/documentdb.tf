resource "aws_docdb_subnet_group" "main" {
  name       = "${var.cluster_name}-docdb"
  subnet_ids = aws_subnet.private[*].id # instances go in PRIVATE Subnet

  tags = { Project = var.cluster_name }
}

resource "aws_security_group" "docdb" {
  name        = "${var.cluster_name}-docdb-sg"
  description = "Allow DocumentDB access only from EKS nodes"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MongoDB port from EKS nodes only"
    from_port       = 27017
    to_port         = 27017
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  tags = { Name = "${var.cluster_name}-docdb-sg" }
}

resource "aws_docdb_cluster" "main" {
  cluster_identifier     = "${var.cluster_name}-docdb"
  engine                 = "docdb"
  master_username        = var.docdb_username
  master_password        = var.docdb_password
  db_subnet_group_name   = aws_docdb_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.docdb.id]
  storage_encrypted      = true
  skip_final_snapshot    = true

  tags = { Project = var.cluster_name }
}

resource "aws_docdb_cluster_instance" "main" {
  cluster_identifier = aws_docdb_cluster.main.id
  instance_class     = "db.t3.medium"

  tags = { Project = var.cluster_name }
}