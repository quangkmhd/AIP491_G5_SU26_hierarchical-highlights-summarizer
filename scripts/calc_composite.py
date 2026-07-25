# Calculating Composite scores for all segmenters based on the new metrics
import numpy as np

# Corpora and their metrics
# each entry: method -> [Pk, WD, F1]
DATA = {
    "dialseg_711": {
        "sliding_texttiling": [0.3657, 0.3743, 0.7077],
        "bamibert_1dod": [0.4474, 0.4477, 0.0104],
        "nltk_texttiling": [0.4736, 0.4790, 0.1850],
        "vibert_texttiling": [0.5071, 0.7016, 0.4013]
    },
    "doc2dial": {
        "sliding_texttiling": [0.5099, 0.5166, 0.6827],
        "bamibert_1dod": [0.4593, 0.4593, 0.0007],
        "nltk_texttiling": [0.5442, 0.5463, 0.2583],
        "vibert_texttiling": [0.5069, 0.5687, 0.4720]
    },
    "meeting_ami": {
        "sliding_texttiling": [0.6427, 0.9889, 0.4709],
        "bamibert_1dod": [0.5585, 0.6968, 0.0445],
        "nltk_texttiling": [0.6199, 0.9428, 0.0244],
        "vibert_texttiling": [0.6471, 0.9993, 0.0307]
    },
    "meeting_committee": {
        "sliding_texttiling": [0.5709, 0.8532, 0.5288],
        "bamibert_1dod": [0.5967, 0.8669, 0.0757],
        "nltk_texttiling": [0.5215, 0.7887, 0.0430],
        "vibert_texttiling": [0.6037, 0.9721, 0.0884]
    },
    "meeting_icsi": {
        "sliding_texttiling": [0.6179, 1.0542, 0.4512],
        "bamibert_1dod": [0.6167, 0.9470, 0.0175],
        "nltk_texttiling": [0.6012, 0.9502, 0.0119],
        "vibert_texttiling": [0.6175, 1.0000, 0.0119]
    },
    "tiage": {
        "sliding_texttiling": [0.4664, 0.4900, 0.6669],
        "bamibert_1dod": [0.4940, 0.4940, 0.0669],
        "nltk_texttiling": [0.5044, 0.5106, 0.1424],
        "vibert_texttiling": [0.4490, 0.5531, 0.4722]
    }
}

methods = ["sliding_texttiling", "bamibert_1dod", "nltk_texttiling", "vibert_texttiling"]
corpus_composites = {m: [] for m in methods}

for corpus, corpus_data in DATA.items():
    # Gather values across methods for this corpus
    pks = [corpus_data[m][0] for m in methods]
    wds = [corpus_data[m][1] for m in methods]
    f1s = [corpus_data[m][2] for m in methods]
    
    pk_min, pk_max = min(pks), max(pks)
    wd_min, wd_max = min(wds), max(wds)
    f1_min, f1_max = min(f1s), max(f1s)
    
    for m in methods:
        val = corpus_data[m]
        pk_val, wd_val, f1_val = val[0], val[1], val[2]
        
        # Pk and WD: lower is better
        s_pk = 1.0 - (pk_val - pk_min) / (pk_max - pk_min) if pk_max != pk_min else 1.0
        s_wd = 1.0 - (wd_val - wd_min) / (wd_max - wd_min) if wd_max != wd_min else 1.0
        # F1: higher is better
        s_f1 = (f1_val - f1_min) / (f1_max - f1_min) if f1_max != f1_min else 1.0
        
        comp = (s_pk + s_wd + s_f1) / 3.0
        corpus_composites[m].append(comp)

# Compute averages
print("=== New Composite Scores ===")
for m in methods:
    mean_comp = np.mean(corpus_composites[m])
    # Compute averages of Pk, WD, F1
    mean_pk = np.mean([DATA[c][m][0] for c in DATA])
    mean_wd = np.mean([DATA[c][m][1] for c in DATA])
    mean_f1 = np.mean([DATA[c][m][2] for c in DATA])
    print(f"Method: {m}")
    print(f"  Composite: {mean_comp:.4f}")
    print(f"  Mean Pk:   {mean_pk:.4f}")
    print(f"  Mean WD:   {mean_wd:.4f}")
    print(f"  Mean F1:   {mean_f1:.4f}")
