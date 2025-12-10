#!/bin/bash
# K8s News Agent Deployment Script
# Minikube'da tüm servisleri build ve deploy eder

set -e

echo "==================================="
echo "K8s NEWS AGENT DEPLOYMENT"
echo "==================================="

# Check minikube
echo "[1/7] Checking minikube..."
if ! minikube status | grep -q "Running"; then
    echo "ERROR: Minikube is not running!"
    echo "Run: minikube start --memory=6144 --cpus=4 --driver=docker"
    exit 1
fi
echo "Minikube OK"

# Set docker env
echo "[2/7] Setting docker environment..."
eval $(minikube docker-env)
echo "Docker env set to minikube"

# Build images
echo "[3/7] Building Docker images..."

cd /Users/yamacbezirgan/Desktop/kkb-hackathon-goldenhead/backend

echo "  - Building news-llm-gateway..."
docker build -t news-llm-gateway:latest ./llm-gateway/

echo "  - Building news-orchestrator..."
docker build -t news-orchestrator:latest ./news-orchestrator/

echo "  - Building news-universal-scraper..."
docker build -t news-universal-scraper:latest ./universal-scraper/

# Optional: Browser Pool (heavyweight, skip if resources limited)
# echo "  - Building news-browser-pool..."
# docker build -t news-browser-pool:latest ./browser-pool/

echo "Docker images built"

# Apply K8s manifests
echo "[4/7] Applying namespace..."
kubectl apply -f k8s/namespace.yaml

echo "[5/7] Applying ConfigMaps..."
kubectl apply -f k8s/configmaps/

echo "[6/7] Deploying services..."

# LLM Gateway
kubectl apply -f k8s/services/llm-gateway/deployment.yaml

# News Orchestrator
kubectl apply -f k8s/services/orchestrator/deployment.yaml

# All Scrapers (10 deployments)
kubectl apply -f k8s/services/scrapers/all-scrapers.yaml

# Optional: Browser Pool
# kubectl apply -f k8s/services/browser-pool/deployment.yaml

echo "[7/7] Verifying deployment..."
sleep 5

echo ""
echo "==================================="
echo "DEPLOYMENT STATUS"
echo "==================================="
kubectl get pods -n news-agent

echo ""
echo "==================================="
echo "SERVICES"
echo "==================================="
kubectl get svc -n news-agent

echo ""
echo "==================================="
echo "USAGE"
echo "==================================="
echo "Port forward orchestrator:"
echo "  kubectl port-forward -n news-agent svc/news-orchestrator 8080:8080"
echo ""
echo "Test:"
echo "  curl -X POST http://localhost:8080/api/news/search \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"company_name\": \"ASELSAN\"}'"
echo ""
echo "Watch pods:"
echo "  kubectl get pods -n news-agent -w"
echo ""
echo "Logs:"
echo "  kubectl logs -n news-agent deployment/news-orchestrator -f"
echo ""
echo "==================================="
echo "DONE!"
echo "==================================="
