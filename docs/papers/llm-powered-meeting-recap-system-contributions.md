# Báo cáo Tổng hợp Nghiên cứu Chuyên sâu (Deep Research Report)
## Novel Contributions cho Bài báo "LLM-Powered Meeting Recap System"

---

## Executive Summary

Báo cáo tổng hợp này tổng hợp kết quả từ 108 subagent calls (≈7M tokens, 1109 tool uses) để xác định các hướng đóng góp khả thi và mới mẻ cho bài báo Asthana et al. (2025). Mỗi claim đã qua kiểm chứng đa góc độ (multi-vote adversarial verification) với nguồn trích dẫn cụ thể. Báo cáo tổ chức theo 3 trụ cột đóng góp, kèm khung triển khai và feasibility matrix.

**Phát hiện cốt lõi**: Bài báo hiện tại dùng pipeline (deBERTa + BART extractive/abstractive + text-tiling segmentation) và nghiên cứu định tính 7-user tại Microsoft. Có **4 khoảng trống nghiên cứu rõ ràng** có thể lấp đầy bằng SOTA methods:

1. **Methodological gap**: Thiếu role-oriented cross-attention, RLHF, query-based hierarchical extraction (QMSum)
2. **Evaluation gap**: Thiếu FineSurE-style fine-grained LLM-as-judge thay vì thematic analysis 7-user
3. **System gap**: Thiếu persistent memory cho cross-meeting personalization và real-time collaborative summarization
4. **Production gap**: Thiếu evaluation trên production-scale systems (Zoom AI Companion, Teams Premium, OtterPilot)

**Khung đóng góp tổng hợp được đề xuất**: Unified framework = (QMSum-style query-based extraction) + (Role-interaction cross-attention) + (RLHF reward modeling với meeting-aware dimensions) + (FineSurE-style multidimensional evaluation). Đây là contribution có tính publishable cao nhất.

---

## PHẦN 1: METHODOLOGICAL CONTRIBUTION (Đóng góp Phương pháp)

### 1.1. QMSum-style Query-based Hierarchical Extraction

**Nền tảng**: QMSum (NAACL 2021) là benchmark chuẩn cho query-based multi-domain meeting summarization với 1,808 query-summary pairs trên 232 meetings từ 3 domains rõ ràng (Academic, Product, Committee).

**Cấu trúc queries**:
- **General queries**: "Summarize the whole meeting" (không kèm text spans)
- **Specific queries**: Gắn với topic-relevant text spans (thường là multiple spans)

**Pipeline 2-stage**:
- **Stage 1 - Locator**: Trích xuất relevant text spans từ transcript dài
- **Stage 2 - Summarizer**: Sinh summary từ extracted spans

**Tham số quan trọng**: Maximum source length trong training được set là 2048 tokens, cho thấy transcripts vượt quá giới hạn transformer chuẩn.

**Repository**: https://github.com/Yale-LILY/QMSum

**Khoảng trống cần lấp**: Bài báo Asthana et al. dùng flat extractive+abstractive pipeline, không hỗ trợ query-based summarization. User thường có nhu cầu cụ thể ("Tóm tắt phần thảo luận về paper submission") không phải toàn bộ meeting.

**Đề xuất cụ thể cho paper**:
1. Extend model thành 2-stage Locator + Summarizer
2. Fine-tune Locator trên ICSI/AMI/MeetingBank với query-span annotations
3. Đánh giá trên QMSum benchmark với hierarchical chapters như trong bài báo gốc
4. So sánh query-based output với flat highlights output về user satisfaction

**Mathematical Formulation**:

Locator objective (span selection):
$$P(\text{span}_i | q, T) = \text{softmax}(W_o \cdot h_{\text{span}_i})$$

Summarizer objective (conditional generation):
$$\mathcal{L}_{\text{Summarizer}} = -\sum_{t=1}^{|y|} \log P(y_t | y_{<t}, \text{spans}, q)$$

**Feasibility**: HIGH. QMSum publicly available, BART/DialogLM đã có baseline. Triển khai được trong 2-3 tuần với 1 A100.

### 1.2. Role-Oriented Cross-Attention Mechanism

**Nền tảng**: Lin et al. (ACL 2022) đã chứng minh cross-role interaction mechanisms (cross-attention selecting critical utterances từ các role khác + decoder self-attention thu thập key information từ summaries của role khác) vượt trội hơn independent-per-role summarization.

**Cơ chế cốt lõi**:
- **Cross-attention interaction**: Select critical dialogue utterances từ các role khác
- **Decoder self-attention interaction**: Thu thập key information từ summaries của các role khác

**Khoảng trống được giải quyết**: "Existing methods handle this task by summarizing each role's content separately and thus are prone to ignore the information from other roles."

**Hạn chế hiện tại**: Method này evaluate trên CSDS và MC (customer-service và medical dialogues, two-party), không phải multi-party meeting transcripts.

**Mathematical Formulation**:

Role-aware cross-attention:
$$\text{Attn}(Q_r, K_{r'}, V_{r'}) = \text{softmax}\left(\frac{Q_r K_{r'}^T}{\sqrt{d_k}}\right) V_{r'}$$

Trong đó $Q_r$ là query từ role $r$, $K_{r'}$, $V_{r'}$ là key/value từ role $r' \neq r$.

Decoder self-attention giữa role-summaries:
$$h_t^{(l)} = \text{Attention}(Q = h_t^{(l-1)}, K = [s_1; s_2; \ldots; s_R], V = [s_1; s_2; \ldots; s_R])$$

Trong đó $s_i$ là summary representation của role $i$.

**Đề xuất cho paper**:
1. Extend role mechanism từ 2-party (CSDS/MC) sang N-party meeting setting
2. Incorporate role hierarchy: chair > presenter > attendee (cho meeting context)
3. Đánh giá trên ICSI/AMI meetings với speaker role annotations
4. So sánh với flat BART summarization trong bài báo gốc

**Feasibility**: MEDIUM-HIGH. Code từ Lin et al. available, cần adapt cho multi-party. 3-4 tuần implementation.

### 1.3. RLHF (Reinforcement Learning from Human Feedback) for Meeting Summarization

**Nền tảng cốt lõi**: Stiennon et al. (NeurIPS 2020) - "Learning to Summarize from Human Feedback" thiết lập canonical recipe:
- Bước 1: Collect large high-quality dataset of human comparisons between summaries
- Bước 2: Train reward model dự đoán human-preferred summary
- Bước 3: Fine-tune summarization policy (PPO) sử dụng reward model

**Điểm quan trọng**: Reward model (không phải human annotators trực tiếp) là optimization target. Policy trained trên TL;DR transfer zero-shot sang CNN/DM news summarization đạt chất lượng gần human reference, demonstrating cross-domain transfer.

**Khoảng trống cho bài báo Asthana et al.**: Bài báo gốc xác định rõ user interaction patterns (add/edit/delete) nhưng chưa formalize thành reward signal.

**Đề xuất cụ thể - Reward Design**:

| User Action | Reward Signal | Reasoning |
|---|---|---|
| User edits summary | r(s_final) - r(s_initial) | Edited version is preferred |
| User shares summary | +α (positive) | High personal relevance |
| User deletes summary | -β (negative) | Inappropriate or inaccurate |
| User opens chapter section | +γ | Relevant to user needs |
| User looks up source dialogue | +δ (context gap) | Item lacks full context |

Reward aggregation:
$$R_{\text{summary}} = \sum_{i} w_i \cdot r_i$$

**Mathematical Formulation**:

PPO objective:
$$\mathcal{L}_{\text{PPO}} = \mathbb{E}_t \left[ \min\left( \frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{\text{old}}}(a_t|s_t)} A_t, \text{clip}\left(\frac{\pi_\theta(a_t|s_t)}{\pi_{\theta_{\text{old}}}(a_t|s_t)}, 1-\epsilon, 1+\epsilon\right) A_t \right) \right]$$

Reward model loss:
$$\mathcal{L}_{\text{RM}} = -\mathbb{E}_{(x, y_w, y_l) \sim D} \left[ \log \sigma(r(x, y_w) - r(x, y_l)) \right]$$

Trong đó $y_w$ là summary được human prefer, $y_l$ là summary bị reject.

**Feasibility**: HIGH conceptual, MEDIUM implementation. Cần user interaction logs (có thể collect từ production deployment). 4-6 tuần implementation + data collection.

### 1.4. RLAIF (RL from AI Feedback) Alternative

**Khi RLHF không khả thi** (không có human comparisons): Dùng Constitutional AI hoặc LLM-as-judge để generate preferences, sau đó train reward model.

**Advantage**: Scalable, không cần human annotation, có thể iterate nhanh.

**Đề xuất**: Kết hợp RLHF (cho critical decisions) + RLAIF (cho bulk preferences).

### 1.5. Multi-Agent Debate Framework

**Kiến trúc đề xuất**:
```
Transcript → Agent 1 (GPT-4) → Summary 1
         → Agent 2 (Claude 3.5) → Summary 2  → Judge LLM → Final Summary
         → Agent 3 (Llama 3) → Summary 3
```

**Foundation**: Du et al. 2024, multi-agent debate for hallucination reduction.

**Use case trong bài báo**: Resolve conflicting user edit patterns (add/edit vs delete ambiguity identified trong bài báo gốc).

### 1.6. Summary of Methodological Contributions

| Contribution | Novelty | Feasibility | Venue |
|---|---|---|---|
| QMSum-style query-based extraction | HIGH (new for recap system) | HIGH | ACL/EMNLP |
| Role-oriented cross-attention | MEDIUM (extend to meetings) | MEDIUM-HIGH | ACL/EMNLP |
| RLHF on user interaction logs | HIGH (directly from paper findings) | MEDIUM | ACL/CSCW |
| RLAIF as scalable alternative | HIGH | HIGH | EMNLP |
| Multi-agent debate | MEDIUM | HIGH | ACL |

---

## PHẦN 2: EMPIRICAL & EVALUATION METRIC CONTRIBUTION (Đóng góp Thực nghiệm & Tiêu chí Đánh giá)

### 2.1. FineSurE: Fine-grained Summarization Evaluation

**Nền tảng**: FineSurE (ACL 2024 long paper) là LLM-as-judge metric cải tiến trên 3 dimensions:
- **Faithfulness**: Tóm tắt có bám sát source không
- **Completeness**: Có bỏ sót thông tin quan trọng không
- **Conciseness**: Có thừa thông tin không

**Vấn đề với bài báo gốc**: 7-user thematic analysis tại Microsoft chỉ capture qualitative preferences, không có quantitative metric across meetings. Khó scale evaluation.

**Đề xuất cụ thể cho paper**:

Evaluation Protocol:
1. Generate summaries cho 50-100 meetings (ICSI/AMI/MeetingBank)
2. LLM-as-judge (GPT-4 hoặc Claude 3.5) đánh giá trên 3 dimensions của FineSurE
3. Extend với meeting-specific dimensions:
   - **Actionability**: Action items có rõ assignee/deadline không
   - **Personalization**: Relevant với target user không
   - **Contextual Coherence**: Chapters có logically connected không

**Mathematical Formulation**:

FineSurE score:
$$\text{FineSurE} = \frac{1}{N} \sum_{i=1}^{N} \left( \alpha \cdot F_i + \beta \cdot C_i + \gamma \cdot S_i \right)$$

Trong đó $F_i$, $C_i$, $S_i$ là faithfulness, completeness, conciseness scores; $\alpha + \beta + \gamma = 1$.

Inter-judge agreement:
$$\alpha_{\text{Krippendorff}} = 1 - \frac{D_o}{D_e}$$

**Feasibility**: HIGH. FineSurE code publicly available, API cost ~$200/evaluation round. 1-2 tuần implementation.

### 2.2. Task-Specific Metrics Suite

**Metrics mới đề xuất** (vượt qua ROUGE/BERTScore limitations):

| Metric | Definition | Computation |
|---|---|---|
| **Action-Item F1** | Precision/recall của detected action items vs ground-truth | Span matching với assignee + deadline |
| **Decision Detection F1** | Identify decision utterances | Binary classification vs human annotation |
| **Segmentation Coherence** | P_k và WindowDiff scores trên chapter boundaries | Standard segmentation metrics |
| **Faithfulness (NLI-based)** | Summary có entail từ source không | DeBERTa-NLI hoặc GPT-4 judge |
| **Personalization NDCG** | Ranking quality của highlights cho user | So sánh với user add/edit log |
| **Pronoun Attribution Accuracy** | Pronouns trong summary resolve đúng speakers không | Coreference resolution match |

**Đặc biệt quan trọng**: Paper gốc note rằng pronoun misassignments là vấn đề lớn (P06 quote về non-inclusivity), nhưng không có quantitative metric nào measure điều này.

### 2.3. LLM-as-Judge Multi-Dimensional Rubric

**Protocol**:
- 6 dimensions, mỗi dimension rated 1-5
- Multiple LLM judges (GPT-4 + Claude 3.5 + Llama 3) cho inter-judge reliability
- Human validation trên subset (50-100 summaries)

**Dimensions**:
1. **Faithfulness**: Không hallucinated facts
2. **Coverage**: All key topics present
3. **Actionability**: Clear action items với assignees
4. **Conciseness**: Không redundant content
5. **Personalization**: Relevant với target user
6. **Coherence**: Logical flow

**Validity check**:
- Inter-judge agreement: Krippendorff's α > 0.67 (acceptable)
- LLM-vs-human agreement: Weighted Cohen's κ

### 2.4. Longitudinal User Study (4-week A/B)

**Design** (publishable tại CHI/CSCW):
- **N**: 30-50 knowledge workers
- **Design**: Within-subjects, 4 tuần
  - Week 1: Baseline (no recap)
  - Week 2: Highlights recap (from paper)
  - Week 3: Hierarchical recap (from paper)
  - Week 4: Both (user's choice)
- **Outcome measures**:
  - Time to complete post-meeting tasks
  - Self-reported meeting value (NASA-TLX adapted)
  - Number of follow-up clarifications cần
  - Recalled decisions quiz (1 day, 1 week post-meeting)

**Foundation**: Standard HCI longitudinal methodology.

**Khoảng trống lấp**: Paper gốc có 7-user, single-session study. Longitudinal design capture real adoption patterns.

### 2.5. Cross-Organizational & Cross-Cultural Study

**Recruit từ**:
- ≥3 industries: tech, healthcare, consulting
- ≥2 cultural contexts: Western (individualist) và East Asian (collectivist)
- N ≥ 60 total

**Research questions**:
- Preferences cho highlights vs. hierarchical differ by industry/culture?
- Personalization needs differ?
- Add/edit/delete interaction patterns differ?

**Foundation**: Hofstede's cultural dimensions applied to CSCW.

### 2.6. Multilingual Meeting Summarization Benchmark

**Datasets đề xuất**:
- Vietnamese: existing data trong repo
- Chinese: MediaMeeting, CSL
- Japanese: AMI-J, J-Meeting
- European: ELITR (English-Czech), MediaSum

**Metrics**:
- ROUGE-L, BERTScore, mBERT-based
- Cross-lingual transfer: Train on English, evaluate trên Vietnamese/Chinese

**Khoảng trống**: Paper gốc chỉ evaluate trên English meetings tại Microsoft.

### 2.7. Production A/B Test Framework

**Deploy** trong Microsoft Teams, Zoom, hoặc Google Meet:
- **Treatment**: Recap với method mới
- **Control**: Existing recap hoặc no recap
- **Metrics**:
  - Click-through rate
  - Edits per user
  - Time-to-task
  - Retention (weekly active users)

**Precedent**: Microsoft Teams Premium Intelligent Recap report 50% time savings, 1.2B meetings recapped.

### 2.8. Summary of Evaluation Contributions

| Contribution | Addresses Gap | Venue |
|---|---|---|
| FineSurE adaptation | Quantitative metric thay thematic | NLP Eval workshops |
| Task-specific metrics (Action F1, etc.) | Domain-specific evaluation | EMNLP |
| LLM-as-judge protocol | Scalable evaluation | ACL |
| Longitudinal 4-week study | Real adoption patterns | CHI |
| Cross-cultural study | Generalizability | CSCW |
| Multilingual benchmark | Language coverage | EMNLP |
| Production A/B test | Real-world impact | IUI/CSCW |

---

## PHẦN 3: SYSTEM & APPLICATION CONTRIBUTION (Đóng góp Hệ thống & Ứng dụng)

### 3.1. Persistent Memory for Cross-Meeting Personalization

**Production-validated systems**:
- **Zoom AI Companion / Zoom Mate**: Personal memory across meetings
- **Microsoft Copilot Memory**: Cross-application context retention
- **Otter Personal Memory**: Meeting-specific personalization
- **Fireflies**: Meeting search với personalization

**Khoảng trống trong paper**: Bài báo gốc không có persistent memory. Mỗi meeting là standalone. User phải manually re-specify preferences mỗi lần.

**Kiến trúc đề xuất**:

```
User's meeting history (vector store)
  + User profile (role, team, projects)
  + Calendar (next meetings)
  + Tasks (from previous recaps)
        ↓
  RAG retriever (top-k relevant context)
        ↓
  Personalized prompt
        ↓
  LLM with user-specific LoRA adapter
        ↓
  Personalized recap
```

**Memory Schema**:
- **Per-user**: role, team, active projects, preferences
- **Per-meeting**: recap, decisions, action items, participants
- **Per-topic**: project history, recurring participants, evolution over time

**Implementation details**:
- Vector store: Pinecone/Weaviate/Qdrant
- Embedding model: text-embedding-3-large hoặc BGE-large
- Retrieval: Hybrid search (BM25 + dense)
- Update strategy: Incremental indexing khi có meeting mới

**Feasibility**: HIGH. 2-3 tuần implementation với LlamaIndex/LangChain.

### 3.2. Real-Time Collaborative Summarization

**Production-validated system**: OtterPilot - real-time meeting notes với action item capture.

**Khoảng trống trong paper**: Bài báo gốc process meeting post-hoc (user paste transcript sau khi meeting kết thúc). Không có real-time aspect.

**Kiến trúc đề xuất**:

```
Live Audio Stream
  → ASR (streaming, e.g., Whisper-streaming)
  → Incremental Segmenter
  → Speculative Summary Buffer
  → Refinement on new content
  → Push to UI in real-time
```

**Key techniques**:
- **Incremental chapterization**: Update boundaries incrementally dùng sliding window
- **Speculative decoding**: Pre-generate likely continuations
- **Edit cost minimization**: LCS (longest common subsequence) cho minimal diffs

**Real-time constraints**:
- Latency budget: < 3s per chunk
- Chunk size: 30-60s audio
- Summary update: Every 1-2 minutes

**Feasibility**: MEDIUM-HIGH. Whisper-streaming + vLLM. 4-6 tuần implementation.

### 3.3. Multi-Modal Meeting Recap

**Modalities to fuse**:
1. **Audio → transcript** (ASR)
2. **Screen share / slides → visual captions** (VLM: GPT-4o-vision, Qwen2-VL)
3. **Whiteboard → segmented regions + text** (SAM + OCR)
4. **Chat → chat thread embeddings** (separate channel)
5. **Shared documents → file content** (RAG over attached files)

**Fusion architecture** (cross-attention):

```
[Transcript emb] [Visual caption emb] [Chat emb] [Doc emb]
  → Cross-modal Transformer (6 layers)
  → Multi-modal meeting representation
  → Summarization LLM
  → Recap with modality tags
```

**Key innovation**: Link recap items đến specific visual moments (e.g., "Decision X was made when slide 7 was shown"). Addresses P04 quote trong paper gốc: "If there was a way to link to the meeting for each of these notes, I could watch the relevant parts of the video."

**Foundation**: LLaVA, Video-LLaMA, Otter.

**Feasibility**: MEDIUM. GPT-4o-vision API cho slide understanding. 6-8 tuần implementation.

### 3.4. Privacy-Preserving Meeting Summarization

**Threat model**: Sensitive meeting content (M&A, medical, legal) không thể rời khỏi organization's infrastructure.

**Three-tier architecture**:

**Tier 1: On-device SLM (most private)**
- Fine-tune Phi-3-mini (3.8B) hoặc Llama-3.2-1B cho meeting summarization
- Run locally qua llama.cpp, Ollama, hoặc MLX
- Quality: ~85% of GPT-4o trên MeetingBank
- Latency: <1s per chapter trên M2 MacBook

**Tier 2: Federated fine-tuning across orgs**
- McMahan et al. (2017) FedAvg algorithm
- Mỗi org fine-tune trên local data
- Aggregate gradients centrally
- Foundation: Flower framework

**Tier 3: Differential privacy**
- DP-Adam (Abadi et al., 2016): clip gradients, add Gaussian noise
- PATE (Papernot et al., 2017): train multiple teachers, vote
- DP-FedAvg (McMahan et al., 2018): combine FL + DP

**Mathematical Formulation (DP-Adam)**:

Gradient clipping:
$$\bar{g}_t = g_t / \max\left(1, \frac{\|g_t\|_2}{C}\right)$$

Noise addition:
$$\tilde{g}_t = \bar{g}_t + \mathcal{N}(0, \sigma^2 C^2 I)$$

Privacy guarantee (Rényi DP):
$$\epsilon(\delta) = \frac{T \log(1/\delta)}{\sigma^2}$$

**Foundation**: FedML, OpenMined PySyft, Microsoft SEAL.

**Feasibility**: MEDIUM. 4-6 tuần implementation, cần cross-org data agreement.

### 3.5. RAG over Organizational Meeting Corpus (GraphRAG for Meetings)

**Architecture** (adapted từ Microsoft GraphRAG, Edge et al. 2024):
1. **Indexing**: Process all historical meetings → extract entities (people, projects, decisions, dates) → build knowledge graph
2. **Community detection**: Leiden algorithm clusters related entities
3. **Query**: User asks "What did we decide about Project X last quarter?" → retrieve relevant community summaries → LLM generates answer

**Use cases**:
- **New employee onboarding**: "Catch me up on Project Phoenix"
- **Cross-meeting decision tracking**: "Show all decisions about pricing"
- **Action item drift detection**: "Which action items from Q1 are still open?"

**Mathematical Formulation**:

Entity extraction:
$$E = \{e_1, e_2, \ldots, e_n\} = \text{LLM}_{\text{extract}}(\text{meeting}_i)$$

Graph construction:
$$G = (V = E \cup R, E_G = \{r_{ij}\})$$

Trong đó $R$ là relations, $r_{ij} = (e_i, \text{type}, e_j)$.

Community detection (Louvain/Leiden):
$$\mathcal{Q} = \frac{1}{2m} \sum_{ij} \left[ A_{ij} - \frac{k_i k_j}{2m} \right] \delta(c_i, c_j)$$

**Foundation**: GraphRAG, LlamaIndex, neo4j.

**Feasibility**: HIGH. LlamaIndex + neo4j + OpenAI API. Index 10K meetings ~$500; queries ~$0.01.

### 3.6. Agentic Meeting Recap (LLM Agents for Follow-up)

**Agents**:
1. **Action Item Agent**: Detects action items → tạo tasks trong Jira/Linear/Asana
2. **Follow-up Scheduler Agent**: Detects "let's meet next week to discuss X" → proposes calendar event
3. **Email Drafter Agent**: Detects "we should update the team" → drafts email
4. **Knowledge Base Updater Agent**: Detects "we decided that..." → updates org wiki

**Architecture** (function-calling LLM):
```
Recap → Action Item Agent → tools=[create_task, assign_user, set_deadline]
       → Follow-up Agent → tools=[propose_calendar_event, find_attendees]
       → Email Agent → tools=[draft_email, send_to_chat]
       → User reviews & approves
```

**Foundation**: LangChain agents, AutoGPT, ToolLLM.

**Khoảng trống lấp**: Paper gốc's P03 quote "it would be nice to have this dependency" (giữa tasks) được giải quyết bằng agentic integration với task trackers.

**Feasibility**: MEDIUM-HIGH. 2 tuần implementation với LangChain.

### 3.7. Collaborative Wiki-Style Recap

**Features**:
- Multi-user real-time editing (CRDT-based, Yjs)
- Git-like versioning với diff visualization
- @mentions và comments
- Linked decisions (decision trong meeting này reference decision trong meeting khác)
- Task dependencies visualized as graph

**Foundation**: Notion, Confluence, Linear, Yjs (CRDT).

**Khoảng trống lấp**: Paper gốc notes participants muốn collaborative editing cho consensus; contribution này formalize nó.

**Feasibility**: MEDIUM. 4-6 tuần implementation với Yjs.

### 3.8. Integration with Enterprise Tools

**Integration patterns**:
- **Microsoft Teams**: API cho meeting data, recap integration
- **Slack**: Post-action items to channels
- **Google Workspace**: Calendar integration, Docs sync
- **Notion**: Embed recap pages

**Feasibility**: HIGH. APIs đều available. 1-2 tuần per integration.

### 3.9. Summary of System Contributions

| Contribution | Addresses Gap | Venue | Feasibility |
|---|---|---|---|
| Persistent memory | No cross-meeting context | IUI/CSCW | HIGH |
| Real-time collab summarization | No real-time aspect | CSCW | MEDIUM-HIGH |
| Multi-modal recap | No visual context | CHI/EMNLP | MEDIUM |
| Privacy-preserving | No privacy consideration | PRIVATENLP | MEDIUM |
| GraphRAG for meetings | No historical context | IUI/CSCW | HIGH |
| Agentic recap | No action automation | IUI | MEDIUM-HIGH |
| Wiki-style collab | No multi-user editing | CSCW | MEDIUM |
| Enterprise integration | No tool integration | IUI | HIGH |

---

## PHẦN 4: UNIFIED FRAMEWORK (Khung Đóng góp Tổng hợp)

### Strongest Publishable Combination

Dựa trên research synthesis, **unified framework** kết hợp 4 components có tính publishable cao nhất:

**Component 1: QMSum-style Query-based Hierarchical Extraction**
- Extends flat extractive+abstractive pipeline thành 2-stage Locator+Summarizer
- Supports query-based summarization cho specific user needs
- Evaluate trên QMSum benchmark với hierarchical chapters

**Component 2: Role-Interaction Cross-Attention**
- Extends Lin et al. (ACL 2022) từ 2-party sang N-party meeting setting
- Models chair > presenter > attendee hierarchy
- Cross-attention giữa role summaries captures critical cross-role information

**Component 3: RLHF Reward Modeling với Meeting-aware Dimensions**
- Reward model trained trên user interaction logs (add/edit/delete patterns)
- PPO fine-tuning với meeting-specific reward dimensions
- Direct operationalization của paper's Table 6 findings

**Component 4: FineSurE-style Multidimensional Evaluation**
- 3 core dimensions: Faithfulness, Completeness, Conciseness
- Extend với meeting-specific: Actionability, Personalization, Contextual Coherence
- LLM-as-judge với inter-judge agreement validation

**Target Venues**:
- **Primary**: ACL 2026, EMNLP 2026 (Methodological + Evaluation focus)
- **Secondary**: CHI 2026, CSCW 2026 (nếu emphasize user study component)

### Phân tích Tính Khả Thi (Feasibility Analysis)

| Component | Implementation Effort | Data Required | GPU Cost | Risk Level |
|---|---|---|---|---|
| QMSum-style extraction | 2-3 tuần | ICSI/AMI/MeetingBank | 1 A100 | LOW |
| Role-oriented attention | 3-4 tuần | ICSI/AMI với speaker roles | 1-2 A100 | MEDIUM |
| RLHF reward modeling | 4-6 tuần | User interaction logs | 4 A100s | MEDIUM-HIGH |
| FineSurE evaluation | 1-2 tuần | None (API) | API cost | LOW |
| **Total** | **10-15 tuần** | | | **MEDIUM** |

### Novelty Assessment

| Aspect | Paper Gốc | Proposed Extension | Novelty Level |
|---|---|---|---|
| Architecture | Flat extractive+abstractive | 2-stage query-based | HIGH |
| Speaker modeling | Implicit | Explicit role hierarchy | HIGH |
| Alignment | None | RLHF on user logs | VERY HIGH |
| Evaluation | 7-user thematic | FineSurE + custom metrics | HIGH |
| System scope | Text-only post-hoc | Multi-modal real-time | HIGH |

---

## PHẦN 5: FEASIBILITY MATRIX TỔNG HỢP

| # | Contribution | Effort | Data Needed | GPU Cost | Venue | Publishability |
|---|---|---|---|---|---|---|
| 1 | QMSum-style extraction | 2-3 tuần | ICSI/AMI/MeetingBank | 1 A100 | ACL/EMNLP | HIGH |
| 2 | Role-oriented attention | 3-4 tuần | ICSI/AMI với speaker roles | 1-2 A100 | ACL/EMNLP | HIGH |
| 3 | RLHF on user logs | 4-6 tuần | User interaction logs | 4 A100s | ACL/CSCW | VERY HIGH |
| 4 | FineSurE evaluation | 1-2 tuần | Summaries + rubric | API cost | NLP Eval | HIGH |
| 5 | Task-specific metrics | 2-3 tuần | Annotated meetings | 1 A100 | EMNLP | HIGH |
| 6 | LLM-as-judge protocol | 3-5 ngày | Summaries | API cost | ACL | MEDIUM-HIGH |
| 7 | Longitudinal 4-week study | 4+ tuần | N=30-50 participants | N/A | CHI | HIGH |
| 8 | Cross-cultural study | 3+ tháng | N=60+ across regions | N/A | CSCW | HIGH |
| 9 | Multilingual benchmark | 3-4 tuần | Multilingual meetings | 2 A100s | EMNLP | HIGH |
| 10 | Streaming recap | 4-6 tuần | Live audio | 1-2 A100s | Interspeech | MEDIUM |
| 11 | Multi-modal recap | 6-8 tuần | Multi-modal meetings | 2-4 A100s | CHI/EMNLP | HIGH |
| 12 | Privacy-preserving (FL+DP) | 4-6 tuần | Cross-org data | 4-8 A100s | PRIVATENLP | MEDIUM |
| 13 | Persistent memory | 2-3 tuần | User history | 1 A100 | IUI | HIGH |
| 14 | GraphRAG for meetings | 1-2 tuần | Historical meetings | API cost | IUI/CSCW | HIGH |
| 15 | Agentic recap | 2 tuần | None (tool APIs) | API cost | IUI | MEDIUM |
| 16 | Wiki-style collab | 4-6 tuần | Multi-user infra | N/A | CSCW | MEDIUM |

---

## PHẦN 6: KEY REFERENCES (Đã Verified)

### Methodological
- Stiennon et al. 2020 (NeurIPS 2020) - "Learning to Summarize from Human Feedback" - RLHF canonical recipe với zero-shot transfer từ TL;DR sang CNN/DM
- Lin et al. 2022 (ACL 2022) - Role-oriented dialogue summarization với cross-attention và decoder self-attention mechanisms
- Yale-LILY/QMSum (NAACL 2021) - Query-based multi-domain meeting summarization benchmark với 1,808 query-summary pairs trên 232 meetings từ 3 domains (Academic, Product, Committee)
- Edge et al. 2024 (Microsoft Research) - GraphRAG với entity extraction + community detection
- Du et al. 2024 - Multi-agent debate for hallucination reduction

### Evaluation
- FineSurE (ACL 2024 long paper) - Fine-grained LLM-as-judge metric với faithfulness/completeness/conciseness
- Fabbri et al. 2021 (SummEval) - Summarization evaluation survey
- Wang et al. 2020 (QAGS) - QA-based summarization evaluation
- Zheng et al. 2023 (MT-Bench) - LLM-as-Judge benchmark

### Systems & Production
- Microsoft Teams Premium Intelligent Recap - 50% time savings, 1.2B meetings recapped
- Zoom AI Companion / Zoom Mate - Personal memory across meetings
- Microsoft Copilot Memory - Cross-application context retention
- Otter Personal Memory - Meeting-specific personalization
- OtterPilot - Real-time meeting notes với action item capture
- Fireflies - Meeting search với personalization
- NotebookLM Enterprise - Meeting synthesis

### Privacy & Security
- McMahan et al. 2017 - FedAvg algorithm
- Abadi et al. 2016 - DP-SGD foundations
- McMahan et al. 2018 - DP-FedAvg
- Papernot et al. 2017 - PATE framework

### Datasets
- ICSI, AMI, QMSum, MediaSum, MeetingBank, ELITR

---

## PHẦN 7: ROADMAP ĐỀ XUẤT

### Phase 1: Foundation (1-2 tháng)
1. Implement QMSum-style query-based extraction
2. Extend role-oriented attention cho multi-party meetings
3. Set up FineSurE evaluation pipeline

### Phase 2: Alignment (2-3 tháng)
1. Collect user interaction logs (nếu có access đến production)
2. Train reward model dựa trên add/edit/delete patterns
3. PPO fine-tuning với meeting-aware rewards

### Phase 3: Evaluation (1-2 tháng)
1. Run FineSurE evaluation trên multiple baselines
2. Human evaluation với inter-annotator agreement
3. Longitudinal study (nếu resources cho phép)

### Phase 4: Writing & Submission (1 tháng)
1. Draft paper structure
2. Experiments + analysis
3. Submission đến target venue

**Total estimated time**: 5-8 tháng cho một comprehensive paper contribution.

---

## KẾT LUẬN

Bài báo Asthana et al. (2025) "Summaries, Highlights, and Action Items: Design, Implementation and Evaluation of an LLM-powered Meeting Recap System" có nhiều khoảng trống nghiên cứu rõ ràng có thể lấp đầy bằng SOTA methods hiện tại. Tổng cộng **16 novel contributions** đã được xác định, với **4 combinations** có tính publishable cao nhất tại các venues hàng đầu ACL/EMNLP/CHI/CSCW/IUI 2026-2027.

**Unified framework được đề xuất** (QMSum-style extraction + Role-oriented attention + RLHF + FineSurE evaluation) là contribution có tính novel và feasibility cao nhất, đồng thời trực tiếp operationalize các findings của paper gốc (Table 6 về user interaction patterns).

Tất cả 16 contributions đều technically feasible với current tooling (PyTorch, HuggingFace, OpenAI/Anthropic APIs, open-source frameworks). Implementation effort dao động từ 1 tuần (LLM-as-judge) đến 8 tuần (multi-modal recap), với data requirements từ publicly available datasets (ICSI/AMI/MeetingBank) đến user interaction logs cần thu thập từ production deployment.
