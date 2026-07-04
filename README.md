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
   - Converts reference papers in PDF format into markdown using the `datalab_sdk` (DatalabClient).
   - Currently includes reference papers:
     - `2021.sigdial-1.18.pdf` (Xing and Carenini, SIGDIAL-21)
     - `2307.15793v3.pdf`

---

## 🚀 Setup & Usage

### 1. Prerequisites
Ensure you have a Python environment (virtual environment recommended):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # If requirements.txt is created
```
*(Note: If `datalab-sdk` and other dependencies are not installed in the system/env, run `pip install datalab-sdk python-dotenv`)*

### 2. Configuration
Create a `.env` file in the root of this folder and add your Datalab API key:
```env
DATALAB_API_KEY_2=your_api_key_here
```

### 3. Convert PDFs to Markdown
Run the conversion script:
```bash
python3 convert-pdf-to-md.py
```
This will generate `2021.sigdial-1.18.md` and `2307.15793v3.md` in the root folder.
