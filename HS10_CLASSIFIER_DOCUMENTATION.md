# HS10 Data Center Relevance Classifier

## Documentation for LLM-Based Commodity Classification System

This document describes the methodology, technology stack, and operational considerations for classifying HS10 commodity codes by their relevance to AI data center construction and operations.

---

## Table of Contents

1. [Methodology](#1-methodology)
2. [Technology Stack](#2-technology-stack)
3. [Cost and Time Estimates](#3-cost-and-time-estimates)
4. [Caveats and Limitations](#4-caveats-and-limitations)
5. [Future Refinements](#5-future-refinements)

---

## 1. Methodology

### 1.1 Overview

The classifier uses Claude AI (Anthropic's large language model) to evaluate each HS10 commodity code description and determine its relevance to hyperscale AI data center construction and operations. The system leverages **structured tool calling** to ensure consistent, validated output across all classifications.

### 1.2 Classification Schema

Each HS10 code is classified along the following dimensions:

| Field | Type | Description |
|-------|------|-------------|
| `relevance` | Enum: High, Medium, Low | Direct relevance to data center construction/operation |
| `confidence` | Integer (0-100) | Model's confidence in the assessment |
| `primary_category` | Enum (9 options) | Functional category for the product |
| `specific_use` | String | Specific application context (e.g., "GPU accelerators", "cooling tower pumps") |
| `reasoning` | String | Brief explanation for the classification |

### 1.3 Primary Categories

Products are assigned to one of nine categories:

1. **Compute_Hardware** - GPUs, CPUs, memory, PCBs, servers, storage drives, semiconductors
2. **Networking_Telecom** - Fiber optics, switches, routers, transceivers, cables
3. **Cooling_HVAC** - Chillers, cooling towers, CRAH units, fans, pumps, refrigerants
4. **Electrical_Power** - Transformers, switchgear, UPS, batteries, generators, busbars
5. **Building_Structure** - Structural steel, concrete, rebar, insulation, raised floors
6. **Fire_Safety_Security** - Fire suppression, detection systems, security equipment
7. **Specialty_Materials** - Rare earths, copper, aluminum, tantalum, thermal interface materials
8. **Maintenance_Operations** - Maintenance supplies, lubricants, operational consumables
9. **Not_DC_Related** - Products not relevant to data center construction/operation

### 1.4 Relevance Definitions

- **High**: Directly used in data center construction or operation (e.g., GPUs, servers, cooling systems, backup generators)
- **Medium**: Sometimes used in data centers or serves as an indirect input (e.g., general-purpose copper wire, electric motors)
- **Low**: Not relevant to data center applications (e.g., food, textiles, consumer goods)

### 1.5 System Prompt Design

The classifier uses a carefully designed system prompt that:

1. Establishes domain expertise in AI data center construction, operations, and supply chains
2. Provides explicit guidance on relevant product categories
3. Addresses common edge cases (e.g., diesel engines for generators vs. vehicles)
4. Instructs the model to use structured tool output for consistency

### 1.6 Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  Input: unique_hs10_commodities.csv                             │
│  (HS10 code + description pairs)                                │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  For each (code, description) pair:                             │
│    1. Send to Claude API with tool calling                      │
│    2. Force tool use: classify_hs10_code                        │
│    3. Extract structured JSON response                          │
│    4. Append to results                                         │
│    5. Checkpoint every 10 items                                 │
│    6. Rate limit (0.5s delay)                                   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Output: hs10_classification_final.csv                          │
│  (HS10 code + classification fields)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | Claude claude-sonnet-4-20250514 (Anthropic) | Classification intelligence |
| **API Client** | `anthropic` Python SDK | API communication |
| **Data Processing** | `pandas` | CSV I/O and data manipulation |
| **Environment** | Python 3.10+ | Runtime environment |
| **Notebook Interface** | Jupyter (VS Code) | Interactive development |

### 2.2 Key Python Dependencies

```
anthropic>=0.40.0
pandas>=2.0.0
python-dotenv  # (optional, for .env file support)
```

### 2.3 API Configuration

- **Model**: `claude-sonnet-4-20250514`
- **Max Tokens**: 400 per request
- **Tool Choice**: Forced (`{"type": "tool", "name": "classify_hs10_code"}`)
- **Rate Limiting**: 0.5 seconds between requests

### 2.4 File Structure

```
ai-trade-index/
├── hs10_llm_classifier_demo.py    # Main classifier module
├── llm-classifier-all.ipynb        # Production notebook
├── unique_hs10_commodities.csv     # Input: all HS10 codes (~19,424 rows)
├── hs10_classification_progress.csv # Checkpoint file (auto-generated)
├── hs10_classification_final.csv   # Output: classified codes
└── .env.example                    # API key template
```

### 2.5 Key Functions

| Function | Description |
|----------|-------------|
| `classify_single_code(code, description)` | Classify one HS10 code via API |
| `classify_batch(codes_and_descriptions, ...)` | Batch process with checkpointing |
| `resume_batch_classification(...)` | Resume from checkpoint, retry errors |

### 2.6 Error Handling & Resilience

- **Checkpointing**: Progress saved every 10 items to `hs10_classification_progress.csv`
- **Resume Capability**: Automatically skips already-classified codes on restart
- **Error Retry**: Codes with `relevance='Error'` are automatically retried on resume
- **Graceful Degradation**: API errors are logged with error details in the output

---

## 3. Cost and Time Estimates

### 3.1 Dataset Size

- **Total HS10 codes**: ~19,424 unique commodity codes
- **Input tokens per request**: ~200-300 tokens (code + description + system prompt)
- **Output tokens per request**: ~100-150 tokens (structured classification)

### 3.2 Cost Breakdown (Claude claude-sonnet-4-20250514)

| Metric | Estimate |
|--------|----------|
| Input tokens per code | ~250 |
| Output tokens per code | ~125 |
| Total input tokens | ~4.9M |
| Total output tokens | ~2.4M |
| **Input cost** ($3/M tokens) | ~$14.70 |
| **Output cost** ($15/M tokens) | ~$36.00 |
| **Total API cost** | **~$50-60** |

> **Note**: Actual costs may vary based on description length and model pricing changes. The above estimates assume claude-sonnet-4-20250514 pricing as of January 2025.

### 3.3 Time Estimates

| Configuration | Time |
|--------------|------|
| Rate limit delay | 0.5 seconds/request |
| API response time | ~0.5-1.0 seconds/request |
| **Time per code** | ~1-1.5 seconds |
| **Total for 19,424 codes** | **~5.5-8 hours** |

### 3.4 Parallelization Note

The current implementation processes codes sequentially with rate limiting. Processing time could be reduced with:
- Parallel API calls (requires careful rate limit management)
- Batch API features (if available)

---

## 4. Caveats and Limitations

### 4.1 Classification Accuracy

- **LLM Judgment**: Classifications reflect the model's understanding, which may not always align with domain expert opinions
- **Edge Cases**: Ambiguous descriptions (e.g., "pumps" without context) may be misclassified
- **No Ground Truth**: Results have not been validated against a labeled dataset

### 4.2 Data Limitations

- **Description Quality**: Classification accuracy depends heavily on the clarity of HS10 descriptions
- **Abbreviations**: Some codes use abbreviations (NESOI, NSPF) that may confuse the model
- **Updates**: HS code definitions change over time; classifier is trained on general knowledge

### 4.3 Technical Limitations

- **Rate Limits**: Anthropic API has rate limits that constrain throughput
- **API Availability**: Processing depends on API uptime; interruptions require resume
- **Cost Variability**: API pricing may change; costs are estimates only
- **Single Model**: Classification relies on one model's perspective

### 4.4 Reproducibility

- **Model Updates**: Future Claude model versions may produce different classifications
- **Non-Deterministic**: LLM outputs can vary slightly between runs
- **No Caching**: Each classification makes a fresh API call

---

## 5. Future Refinements

### 5.1 Validation & Quality Assurance

- [ ] **Expert Review**: Sample 100-200 codes for manual expert validation
- [ ] **Confusion Analysis**: Identify systematic misclassification patterns
- [ ] **Confidence Calibration**: Verify that confidence scores correlate with accuracy
- [ ] **Inter-Rater Reliability**: Compare against human classifiers on a subset

### 5.2 Methodology Improvements

- [ ] **Few-Shot Examples**: Add curated examples to the system prompt for better consistency
- [ ] **Chain-of-Thought**: Use reasoning-focused prompts for edge cases
- [ ] **Multi-Model Ensemble**: Compare classifications across Claude, GPT-4, and others
- [ ] **Hierarchical Classification**: First classify by category, then by relevance
- [ ] **Context Enrichment**: Look up HS code definitions from official sources

### 5.3 Performance Optimization

- [ ] **Batch API**: Use Anthropic's batch processing API for cost/speed improvements
- [ ] **Caching Layer**: Cache results to avoid re-processing unchanged codes
- [ ] **Parallel Processing**: Implement async API calls with proper rate limiting
- [ ] **Incremental Updates**: Only reclassify codes with changed descriptions

### 5.4 Output Enhancements

- [ ] **Subcategory Fields**: Add more granular categorization (e.g., "GPU" vs "CPU" within Compute)
- [ ] **Tariff Line Grouping**: Aggregate classifications to HS6 or HS4 level
- [ ] **Supply Chain Mapping**: Link codes to specific data center construction phases
- [ ] **Time-Series Tracking**: Track how classifications evolve with model updates

### 5.5 Alternative Approaches to Explore

- [ ] **Fine-Tuned Model**: Train a smaller model specifically for HS10 classification
- [ ] **Rule-Based Hybrid**: Combine LLM with rule-based classifier for high-confidence cases
- [ ] **Active Learning**: Use model uncertainty to prioritize human review
- [ ] **Embedding Similarity**: Use semantic embeddings to find similar codes

---

## Appendix: Quick Start

### Running the Classifier

```python
# 1. Set API key (environment variable recommended)
import os
os.environ['ANTHROPIC_API_KEY'] = 'your-api-key'

# 2. Import and run
from hs10_llm_classifier_demo import resume_batch_classification

results = resume_batch_classification(
    all_codes_file='unique_hs10_commodities.csv',
    checkpoint_file='hs10_classification_progress.csv',
    code_column='I_COMMODITY',
    description_column='I_COMMODITY_LDESC',
    output_file='hs10_classification_final.csv',
    delay=0.5
)
```

### Testing a Single Code

```python
from hs10_llm_classifier_demo import classify_single_code

result = classify_single_code(
    "8542310040",
    "PROCESSORS: GRAPHICS PROCESSING UNITS (GPUS)"
)
print(result)
# {'relevance': 'High', 'confidence': 98, 'primary_category': 'Compute_Hardware', ...}
```

---

*Last updated: January 2025*
