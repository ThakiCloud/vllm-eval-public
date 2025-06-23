### **VLLM 모델 성능 자동 평가 PRD v2 (Product Requirements Document)**

---

#### 1. 목적 (Purpose)

쿠버네티스 클러스터에 배포된 **VLLM** 서빙 모델을 **Deepeval** 및 **Evalchemy**로 지속적·자동으로 평가하여

* 모델 릴리스마다 객관적 품질 지표를 확보하고
* 품질 퇴화(regression)를 즉시 탐지하며
* **운영 팀의 Microsoft Teams 채널**에 실시간 리포팅/알림을 제공한다.

#### 2. 배경 (Background)

* **Deepeval**: PyTest‑스타일 단위‑테스트형 LLM 평가 프레임워크로 30+ Metrics, RAG & E2E 평가 지원.
* **Evalchemy**: EleutherAI lm‑evaluation‑harness 기반 Unified Benchmark Runner, 표준 벤치마크와 API‑기반 모델 지원.
* **VLLM**: GPU 메모리 효율을 극대화한 PagedAttention Inference 엔진. 버전 업마다 품질 변동 가능성이 높아 자동화된 Regression Test가 필수.

#### 3. 범위 (Scope)

* **포함**:

  * Deepeval · Evalchemy **내장 데이터셋** 활용 및 **중복 제거된** 테스트 스위트 구성
  * 커스텀 Metric(예: RAG 정답률, Hallucination)
  * 표준 벤치마크 (ARC, HellaSwag, MMLU 등)
  * **파이프라인 트리거: GHCR 이미지** 태그 `release-*` Push 고정
  * 결과 저장(ClickHouse) + Grafana Dashboard + **Microsoft Teams** 알림
* **제외**: 모델 학습/파인튜닝, 클러스터 프로비저닝

#### 4. 이해관계자 (Stakeholders)

* 제품 오너, ML Ops, 리서치, 플랫폼 Ops

#### 5. 성공 지표 (Success Metrics)

| 항목            | 목표값        | 측정 방법             |
| ------------- | ---------- | ----------------- |
| 릴리스‑to‑리포트 지연 | ≤ 2 h      | 파이프라인 완료 타임스탬프    |
| 품질 퇴화 감지율     | ≥ 95 %     | Known‑Bad 리그레션 세트 |
| 파이프라인 안정성     | 실패 < 1 %/월 | CronJob 성공률       |

#### 6. 시스템 아키텍처 (High‑Level Architecture)

1. **Trigger Layer**

   * *Event Source*: **GHCR** Repository Package Push Webhook
   * *Mechanism*: Argo Events → Argo Workflows
2. **Execution Layer – Argo Workflow Steps**

   1. `prepare-dataset`
   2. `deepeval-runner` (GPU=0)
   3. `evalchemy-runner` (GPU=N)
   4. `aggregate-metrics`
3. **Storage & Results**

   * Dataset & Snapshot: MinIO (bucket `llm-eval-ds`)
   * Raw Logs: PVC (7 일 보존)
   * Aggregated Metrics: ClickHouse `vllm_eval.results`
4. **Observability**

   * Prometheus Exporter (파이프라인 Job 상태)
   * Grafana 대시보드 `LLM Quality Overview`
   * **Microsoft Teams Incoming Webhook** `VLLM‑CI` 채널 알림 (Adaptive Card)

#### 7. 기능 요구사항 (Functional Requirements)

* **F‑01** 릴리스 훅: `ghcr.io/{repo}/*` 이미지 Push & `tag =~ /release-.+/` 시 파이프라인 자동 실행
* **F‑02** 데이터셋 버전: `datasets/raw/` 디렉토리 내 데이터셋별 관리
* **F‑03** Deepeval Custom Metric Registry: `eval/deepeval_tests/metrics/*.py`
* **F‑04** Evalchemy Benchmark Selection: `configs/evalchemy.json` 내 `tasks` 목록
* **F‑05** 결과 스키마: `run_id`,`model_tag`,`metric`,`value`,`ts`
* **F‑06** Regression Alert: 최근 N회 Rolling Mean 대비 10 %↓ 시 **Teams Mentions** (@LLM‑Ops)

#### 8. 비기능 요구사항 (Non‑Functional)

* **보안**: ServiceAccount 최소 RBAC, Secrets External Secret 연동
* **성능**: Benchmark Job Timeout ≤ 60 min; GPU Pod PriorityClass = high
* **확장성**: Benchmark Matrix 병렬 Fan‑out
* **가용성**: Argo Workflow Controller HA (2 Replicas)
* **감사 로그**: 모든 RUN\_ID 별 JSONL 로그 S3 ≥ 90 일 보존

#### 9. 데이터셋·벤치마크 (Assets)

| 카테고리     | 예시                   | 관리 방식                     |
| -------- | -------------------- | ------------------------- |
| 표준 벤치마크  | ARC, HellaSwag, MMLU | Evalchemy Preset          |
| 한국어 벤치마크 | Ko‑MMLU, Ko‑ARC      | 별도 bucket `ko-benchmark`  |
| 리그레션 세트  | 서비스 쿼리 스냅샷 1 k       | 일 1 회 익명화 & SHA‑256 Dedup |

**Deduplication** 전략: SHA‑1/256 Hash → Exact Match 제거 → Near‑Dup (LSH + Levenshtein < 0.2) 필터로 Deepeval·Evalchemy 양측 데이터셋 중복 제거.

#### 10. 구현 로드맵 (Timeline)

* **W1‑2** 데이터셋 정의 & 적재, Dedup 파이프 구축
* **W3‑4** Deepeval Metric 프로토타입 + 수동 평가 베이스라인
* **W5‑6** Argo Workflow CI/CD 통합, **Teams 알림** 적용
* **W7** Grafana 대시보드, ClickHouse 리텐션 정책
* **W8** Pilot 릴리스(내부) → 피드백 반영 후 Prod Go‑Live

#### 11. 위험 및 완화 (Risks & Mitigations)

| 위험          | 영향        | 완화책                         |
| ----------- | --------- | --------------------------- |
| 벤치마크 시간 과다  | 릴리스 지연    | 데이터셋 샘플링, GPU 수평 스케일        |
| 평가 지표 해석 오류 | 잘못된 품질 판단 | 리서치 코드 리뷰                   |
| GPU 비용 증가   | 운영 비용 상승  | Spot GPU + Budget Guardrail |

#### 12. 용어 (Glossary)

* **GHCR**: GitHub Container Registry
* **Incoming Webhook**: Teams 채널에 JSON Payload로 메시지 전송
* **Deepeval**: LLM 단위 테스트 프레임워크
* **Evalchemy**: 표준 LLM 벤치마크 실행기
* **VLLM**: 고성능 Inference 엔진
* **Regression Alert**: 배포 버전 대비 성능 하락 경고

---
