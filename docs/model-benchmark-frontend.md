# Model Benchmark Frontend

이 프로젝트는 다양한 모델의 벤치마크 결과를 시각화하고 비교하기 위한 React 기반의 웹 대시보드입니다. Vite를 사용하여 빌드되었으며, 개발 및 프로덕션 환경을 모두 지원합니다.

## ✨ 주요 기능

-   **동적 벤치마크 대시보드**: 모든 벤치마크 결과의 요약 정보를 테이블 형태로 제공합니다.
-   **상세 결과 조회**: 각 결과를 클릭하여 전체 메타데이터, 품질 및 성능 지표를 상세히 확인할 수 있습니다.
-   **결과 필터링**: 모델의 Source, Tokenizer ID, Model ID를 기준으로 결과를 동적으로 필터링할 수 있습니다.
-   **환경 분리 데이터 로딩**:
    -   **개발 환경**: `/public/results/parsed` 디렉토리의 로컬 JSON 파일을 사용하여 빠르게 개발합니다.
    -   **프로덕션 환경**: 서버(Nginx)가 동적으로 제공하는 파일 목록을 가져와 PVC(PersistentVolumeClaim)에 저장된 결과를 런타임에 표시합니다.

## 🛠️ 기술 스택

-   **Frontend**: React, Vite, React Router
-   **Serving (Production)**: Nginx
-   **Containerization**: Docker
-   **Orchestration**: Kubernetes

## 📂 프로젝트 구조

```
/
├── public/
│   └── results/
│       ├── model-results/  # (PVC 마운트 대상) 원본 모델 결과
│       └── parsed/         # (PVC 마운트 대상) 파싱된 JSON 결과 (개발 시 샘플 데이터 위치)
├── src/                    # React 애플리케이션 소스 코드
│   ├── App.jsx
│   ├── main.jsx
│   ├── DashboardPage.jsx   # 메인 대시보드 컴포넌트
│   └── DetailPage.jsx      # 상세 결과 페이지 컴포넌트
├── nginx.conf              # 프로덕션용 Nginx 설정 파일
├── package.json            # 프로젝트 의존성 및 스크립트
```

---

## 🚀 시작하기

### 1. 개발 환경에서 실행하기

**사전 요구사항**: Node.js v18 이상

1.  **저장소 복제 및 이동**:
    ```bash
    git clone <repository_url>
    cd model-benchmark-frontend
    ```

2.  **의존성 설치**:
    ```bash
    npm install
    ```

3.  **샘플 데이터 준비 (중요)**:
    개발 서버는 `public/results/parsed/` 디렉토리에서 결과 파일을 읽습니다. 이 위치에 하나 이상의 샘플 `*.json` 파일을 추가해야 합니다.

4.  **개발 서버 실행**:
    ```bash
    npm run dev
    ```
    이제 브라우저에서 `http://localhost:5173` (또는 터미널에 표시된 주소)로 접속하여 대시보드를 확인할 수 있습니다.

### 2. 프로덕션 배포하기

#### 단계 1: 애플리케이션 빌드

React 애플리케이션을 정적 파일로 빌드합니다. 결과물은 `dist` 폴더에 생성됩니다.

```bash
npm run build
```

#### 단계 2: Docker 이미지 빌드 및 푸시

`Dockerfile`을 사용하여 프로덕션용 Nginx 서버 이미지를 빌드합니다.

```bash
# Docker 이미지 빌드 (your-registry를 실제 레지스트리 주소로 변경)
docker build -t your-registry/model-benchmark-frontend:latest .

# 컨테이너 레지스트리로 이미지 푸시
docker push your-registry/model-benchmark-frontend:latest
```

#### 단계 3: Kubernetes 배포

1.  **매니페스트 수정**:
    -   `k8s/frontend-deployment.yaml` 파일의 `spec.template.spec.containers.image` 필드를 방금 푸시한 Docker 이미지 주소로 수정합니다.
    -   `k8s/frontend-pvc.yaml` 파일의 `spec.storageClassName`을 사용 중인 쿠버네티스 클러스터 환경에 맞는 StorageClass 이름으로 필요시 수정합니다.

2.  **리소스 배포**:
    `kubectl`을 사용하여 PVC와 Deployment, Service를 클러스터에 배포합니다.

    ```bash
    # PVC 생성
    kubectl apply -f k8s/pvc.yaml

    # Deployment 및 Service 생성
    kubectl apply -f k8s/deployment.yaml
    ```

3.  **데이터 업로드**:
    대시보드에 데이터를 표시하려면, 생성된 `parsed-results-pvc` 볼륨에 파싱된 결과 파일(`*.json`)들을 업로드해야 합니다. `kubectl cp`를 사용하거나 파일 업로드를 지원하는 다른 도구를 사용할 수 있습니다.

4.  **접속 확인**:
    `Service`가 `ClusterIP` 타입으로 생성되었으므로, 클러스터 외부에서 접속하려면 `Ingress`를 추가로 설정하거나 `port-forward`를 사용하여 임시로 확인할 수 있습니다.
    ```bash
    # 포트 포워딩으로 로컬에서 접속 테스트
    kubectl port-forward svc/model-platform-frontend-svc 8080:80
    ```
    이후 브라우저에서 `http://localhost:8080`으로 접속합니다. 