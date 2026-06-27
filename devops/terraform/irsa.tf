resource "aws_iam_policy" "backend_secrets_read" {
  name = "${var.cluster_name}-backend-secrets-read"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:travelmemory/docdb-mongo-uri-*"
    }]
  })
}

resource "aws_iam_role" "backend_irsa" {
  name = "${var.cluster_name}-backend-irsa"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = module.eks.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${module.eks.oidc_provider}:sub" = "system:serviceaccount:default:backend-sa"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "backend_irsa_secrets" {
  role       = aws_iam_role.backend_irsa.name
  policy_arn = aws_iam_policy.backend_secrets_read.arn
}