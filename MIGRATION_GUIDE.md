# Green Healthcare Agent Migration Guide

## 1. Environment Setup
```bash
# Ubuntu 20.04+ or similar Linux
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
conda create -n medagent python=3.10
conda activate medagent
pip install -r requirements.txt
```

## 2. Repo Setup
```bash
git clone <REPO_URL> MedAgentBench
cd MedAgentBench
# Expected: green_agent/, src/, data/medagentbench/test_data_v2.json, configs/
git pull  # To update code later
```

## 3. FHIR Server Setup
```bash
sudo apt install docker.io
docker pull stanfordshah/medagentbench:latest
docker run -d -p 8080:8080 stanfordshah/medagentbench:latest
# Verify: Open browser to http://localhost:8080/
```

## 4. Running Green Agent
```bash
export PYTHONPATH=$(pwd)
# Start controller + workers
python src/server/main.py --config configs/controller.yaml &
python src/server/main.py --config configs/workers/worker1.yaml &
# Run assigner
python src/assigner/main.py --config configs/assigner.yaml
# Test one episode locally
python -c "from green_agent.green_healthcare_agent import GreenHealthcareAgent; agent = GreenHealthcareAgent(); print(agent.reset())"
```

## 5. Troubleshooting
```bash
# Docker permission denied → sudo usermod -aG docker $USER && newgrp docker
# ModuleNotFoundError → export PYTHONPATH=$(pwd)
# Git push blocked → ssh-keygen -t ed25519 && cat ~/.ssh/id_ed25519.pub (add to GitHub)
```
