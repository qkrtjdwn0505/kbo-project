#!/bin/bash
set -e

# Python 의존성
pip install -r requirements.txt

# Node.js + React 빌드
cd src/frontend
npm install
npm run build
cd ../..

echo "빌드 완료"
