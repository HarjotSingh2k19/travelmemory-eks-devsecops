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
    }
}
