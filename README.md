# 15-Meeting-summary

This tool serves as a **Dialogue Topic Segmentation Data Hub** and contains reference papers along with a PDF-to-Markdown conversion script.

## 📌 Features

1. **Data Hub (`data/`)**:
   - Maintains and organizes open-sourced data resources for Dialogue Topic Segmentation.
   - Includes standardized datasets:
     - `DialSeg_711` (Xu et al., AAAI-21)
     - `Doc2Dial` (Feng et al., EMNLP-20)
     - `Tiage` (Xie et al., EMNLP Findings-21)
     - `AMI Meeting Corpus` (Carlette et al., 2005)
     - `ICSI Meeting Corpus` (Janin et al., ICASSP-03)
     - `Committee (QMSum)` (Zhong et al., NAACL-21)

2. **PDF Converter (`convert-pdf-to-md.py`)**:
   - Converts reference papers in PDF format into markdown using the `datalab-python-sdk` (DatalabClient).
   - Keeps papers organized under [papers/](file:///home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/papers) and generates outputs under [docs/](file:///home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/docs) with descriptive, product-standard names.
   - Reference papers:
     - [improving-unsupervised-dialogue-topic-segmentation.pdf](file:///home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/papers/improving-unsupervised-dialogue-topic-segmentation.pdf) (Xing and Carenini, SIGDIAL-21)
     - [llm-powered-meeting-recap-system.pdf](file:///home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/papers/llm-powered-meeting-recap-system.pdf) (Asthana et al., 2023)

---

## 🚀 Setup & Usage

### 1. Prerequisites
Ensure you have a Python environment (virtual environment recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install datalab-python-sdk python-dotenv
```

### 2. Configuration
Create a `.env` file in the root of this folder and add your Datalab API key:
```env
DATALAB_API_KEY_2=your_api_key_here
```

### 3. Convert PDFs to Markdown
Run the conversion script:
```bash
.venv/bin/python convert-pdf-to-md.py
```
This will:
1. Convert the PDFs in `papers/` using `DatalabClient` in accurate mode.
2. Generate clean markdown files in `docs/`:
   - [improving-unsupervised-dialogue-topic-segmentation.md](file:///home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/docs/improving-unsupervised-dialogue-topic-segmentation.md)
   - [llm-powered-meeting-recap-system.md](file:///home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/docs/llm-powered-meeting-recap-system.md)
3. Extract and organize all images into separate paper assets folders under `docs/assets/` with clean names (e.g. `figure-1.jpg`), and automatically rewrite the image links inside the markdown files.

