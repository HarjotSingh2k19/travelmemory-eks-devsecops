pipeline {
    agent {
        kubernetes {
            serviceAccount 'jenkins-agent-sa'
            yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: kaniko
      image: gcr.io/kaniko-project/executor:debug
      command: ['sleep']
      args: ['9999999']
    - name: trivy
      image: aquasec/trivy:latest
      command: ['sleep']
      args: ['9999999']
    - name: checkov
      image: bridgecrew/checkov:latest
      command: ['sleep']
      args: ['9999999']
    - name: node
      image: node:20-alpine
      command: ['sleep']
      args: ['9999999']
    - name: gitleaks
      image: zricethezav/gitleaks:latest
      command: ['sleep']
      args: ['9999999']
    - name: python
      image: python:3.12-slim
      command: ['sleep']
      args: ['9999999']
"""
        }
    }
    environment {
        IMAGE_TAG    = "${BUILD_NUMBER}"
        ECR_REGISTRY = "446056240219.dkr.ecr.ap-south-1.amazonaws.com"
    }
    stages {
        stage('1 - Checkout') {
            steps {
                checkout scm
            }
        }
        stage('2 - Unit Tests') {
            steps {
                container('node') {
                    sh '''
                        cd backend
                        echo "MONGO_URI=mongodb://localhost:27017/test" > .env
                        echo "PORT=3000" >> .env
                        npm ci
                        npm test
                    '''
                }
            }
        }
        stage('3 - Secrets Scan') {
            steps {
                container('gitleaks') {
                    sh '''
                        gitleaks detect --source . --report-format json --report-path gitleaks-report.json --exit-code 0
                    '''
                }
            }
        }
        stage('4 - IaC Scan') {
            steps {
                container('checkov') {
                    sh '''
                        checkov -d devops/terraform --output json --output-file-path console > checkov-report.json || true
                    '''
                }
            }
        }
        stage('5 - Build & Push Images (Kaniko)') {
            steps {
                container('kaniko') {
                    sh '''
                        /kaniko/executor \
                          --context=`pwd`/backend \
                          --dockerfile=`pwd`/backend/Dockerfile \
                          --destination=${ECR_REGISTRY}/travelmemory-backend:${IMAGE_TAG} \
                          --destination=${ECR_REGISTRY}/travelmemory-backend:latest

                        /kaniko/executor \
                          --context=`pwd`/frontend \
                          --dockerfile=`pwd`/frontend/Dockerfile \
                          --destination=${ECR_REGISTRY}/travelmemory-frontend:${IMAGE_TAG} \
                          --destination=${ECR_REGISTRY}/travelmemory-frontend:latest
                    '''
                }
            }
        }
        stage('6 - Image Scan (Trivy)') {
            steps {
                container('trivy') {
                    sh '''
                        trivy image --format json -o trivy-backend.json ${ECR_REGISTRY}/travelmemory-backend:${IMAGE_TAG} || true
                        trivy image --format json -o trivy-frontend.json ${ECR_REGISTRY}/travelmemory-frontend:${IMAGE_TAG} || true
                    '''
                }
            }
        }
        stage('7 - AI Triage Gate') {
            steps {
                container('python') {
                    sh '''
                        pip install --quiet anthropic requests
                        python3 scripts/scan-triage.py trivy-backend.json checkov-report.json gitleaks-report.json
                    '''
                }
            }
        }
        stage('8 - Update GitOps Repo') {
            steps {
                sh '''
                    git clone https://${GIT_USER}:${GIT_PAT}@github.com/HarjotSingh2k19/travelmemory-eks-devsecops-gitops.git
                    cd travelmemory-eks-devsecops-gitops
                    sed -i "s/tag:.*/tag: \\"${IMAGE_TAG}\\"/g" helm/values.yaml
                    git config user.email "jenkins@travelmemory.local"
                    git config user.name "Jenkins CI"
                    git commit -am "ci: bump image tag to ${IMAGE_TAG} [skip ci]"
                    git push
                '''
            }
        }
    }
}