#!/usr/bin/env python3
"""Regenerate report figures directly from datasets and training artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT.parent / "16-dts-tsl"
ASSETS = ROOT / "report_compilation" / "assets"
DATA = ROOT / "data"

BLUE = "#0077BB"
CYAN = "#33BBEE"
TEAL = "#009988"
ORANGE = "#EE7733"
RED = "#CC3311"
GRAY = "#6B7280"


def configure_style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Liberation Sans", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def save(fig: plt.Figure, name: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / f"{name}.png", facecolor="white")
    fig.savefig(ASSETS / f"{name}.pdf", facecolor="white")
    plt.close(fig)


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def alimeeting_contents() -> dict[str, list[dict]]:
    return {
        split: [row["content"] for row in load_jsonl(DATA / "Alimeeting4MUG_vi" / f"{split}_vi.jsonl")]
        for split in ("train", "dev", "test")
    }


def segmentation_stats() -> tuple[list[str], list[int], list[int], list[float], list[float]]:
    names = ["dialseg_711", "doc2dial", "meeting_ami", "meeting_committee", "meeting_icsi", "tiage"]
    dialogs: list[int] = []
    utterances: list[int] = []
    avg_utts: list[float] = []
    avg_words: list[float] = []
    for name in names:
        rows = json.loads((DATA / "eval_vi" / f"{name}.json").read_text(encoding="utf-8"))
        texts = [text for row in rows for text in row.get("utterances_vi", row["utterances"])]
        dialogs.append(len(rows))
        utterances.append(len(texts))
        avg_utts.append(len(texts) / len(rows))
        avg_words.append(sum(len(text.split()) for text in texts) / len(texts))
    return names, dialogs, utterances, avg_utts, avg_words


def dataset_length_comparison() -> None:
    names, _, _, avg_utts, avg_words = segmentation_stats()
    ali = alimeeting_contents()
    all_meetings = [row for split in ali.values() for row in split]
    ali_utterances = [sentence["s"] for row in all_meetings for sentence in row["sentences"]]
    plot_names = ["AliMeeting4MUG_vi", *names]
    plot_avg_utts = [len(ali_utterances) / len(all_meetings), *avg_utts]
    plot_avg_words = [sum(len(text.split()) for text in ali_utterances) / len(ali_utterances), *avg_words]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    colors_left = ["#7089D5", "#91A9EB", "#B9CCF2", "#D6D4D4", "#EBC4B1", "#E69B7F", "#D66B58"]
    colors_right = ["#8DB89B", "#70A38F", "#5A958B", "#3F7F83", "#36768A", "#315F82", "#38527B"]
    x = np.arange(len(plot_names))
    bars = axes[0].bar(x, plot_avg_utts, color=colors_left, edgecolor="white")
    axes[0].bar_label(bars, labels=[f"{v:.1f}" for v in plot_avg_utts], padding=3, fontweight="bold")
    axes[0].set_title("Độ dài hội thoại trung bình (Avg Utterances per Dialogue)", fontweight="bold")
    axes[0].set_ylabel("Số lượt lời trung bình (Avg Utterances)")
    bars = axes[1].bar(x, plot_avg_words, color=colors_right, edgecolor="white")
    axes[1].bar_label(bars, labels=[f"{v:.1f}" for v in plot_avg_words], padding=3, fontweight="bold")
    axes[1].set_title("Độ dài lượt lời trung bình (Avg Words per Utterance)", fontweight="bold")
    axes[1].set_ylabel("Số từ trung bình (Avg Words)")
    for ax in axes:
        ax.set_xticks(x, plot_names, rotation=30, ha="right")
        ax.set_xlabel("Bộ dữ liệu (Dataset)")
        ax.grid(axis="y", color="#D1D5DB", linewidth=0.7)
        ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "dataset_length_comparison")


def alimeeting_length_distribution() -> None:
    train = alimeeting_contents()["train"]
    chunk_words: list[int] = []
    summary_words: list[int] = []
    for meeting in train:
        utterance_by_id = {sentence["id"]: sentence["s"] for sentence in meeting["sentences"]}
        for chunk in meeting["chunk_summaries"]:
            chunk_words.append(sum(
                len(utterance_by_id[idx].split())
                for idx in range(chunk["start_id"], chunk["end_id"] + 1)
                if idx in utterance_by_id
            ))
            summary_words.append(len(chunk["summary"].split()))

    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2))
    specs = [
        (axes[0], chunk_words, BLUE, "Độ dài khối hội thoại đầu vào (Chunk Word Count)"),
        (axes[1], summary_words, TEAL, "Độ dài bản tóm tắt mục tiêu (Summary Word Count)"),
    ]
    for ax, values, color, title in specs:
        mean = float(np.mean(values))
        ax.hist(values, bins=25, color=color, alpha=0.68, edgecolor="white")
        ax.axvline(mean, color=RED, linestyle="--", linewidth=1.6, label=f"Trung bình: {mean:.1f} từ")
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Số lượng từ (Words)")
        ax.set_ylabel("Số lượng mẫu (Count)")
        ax.grid(color="#D1D5DB", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.legend(frameon=False)
    fig.tight_layout()
    save(fig, "alimeeting_len_dist")


def eval_history(path: Path) -> list[dict]:
    state = json.loads(path.read_text(encoding="utf-8"))
    rows = [row for row in state["log_history"] if "eval_loss" in row]
    return sorted(rows, key=lambda row: float(row["epoch"]))


def training_history_figure(
    rows: list[dict], name: str, model_name: str, best_epoch: int, checkpoint_label: str
) -> None:
    epochs = [int(row["epoch"]) for row in rows]
    loss = [row["eval_loss"] for row in rows]
    rouge1 = [row["eval_rouge1"] for row in rows]
    rouge_l = [row["eval_rougeL"] for row in rows]

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(7.2, 6.0),
        sharex=True,
        layout="constrained",
        gridspec_kw={"hspace": 0.12},
    )
    axes[0].plot(epochs, loss, color=RED, marker="o", linewidth=1.8, label="Validation loss")
    axes[0].set_ylabel("Validation loss")
    axes[0].legend(frameon=False, loc="best")
    axes[1].plot(epochs, rouge1, color=BLUE, marker="s", linewidth=1.8, label="ROUGE-1")
    axes[1].plot(epochs, rouge_l, color=ORANGE, marker="^", linewidth=1.8, label="ROUGE-L")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("ROUGE score")
    axes[1].legend(frameon=False, ncol=2, loc="best")
    for ax in axes:
        ax.grid(color="#D1D5DB", linestyle="--", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_xticks(epochs)
        ax.axvline(best_epoch, color=TEAL, linestyle=":", linewidth=1.4)
    best_row = next(row for row in rows if int(row["epoch"]) == best_epoch)
    axes[1].annotate(
        f"{checkpoint_label}\nEpoch {best_epoch} · ROUGE-L = {best_row['eval_rougeL']:.4f}",
        xy=(best_epoch, best_row["eval_rougeL"]),
        xytext=(0.52, 0.18),
        textcoords="axes fraction",
        arrowprops={"arrowstyle": "->", "color": TEAL},
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#E8F7F4", "edgecolor": TEAL},
        fontsize=9,
    )
    fig.suptitle(f"Diễn biến đánh giá {model_name} theo epoch", fontsize=13, fontweight="bold")
    save(fig, name)


def main() -> None:
    configure_style()
    dataset_length_comparison()
    alimeeting_length_distribution()
    vit5_path = MODEL_ROOT / "outputs/chunk_summarizer/vit5-chunk-summarizer-v1/checkpoint-7900/trainer_state.json"
    bartpho_path = MODEL_ROOT / "outputs/topic_titler/bartpho-topic-titler-v2/checkpoint-92/trainer_state.json"
    training_history_figure(
        eval_history(vit5_path),
        "vit5_training_history",
        "ViT5",
        best_epoch=6,
        checkpoint_label="Checkpoint được chọn",
    )
    training_history_figure(
        eval_history(bartpho_path),
        "bartpho_training_history_new",
        "BARTpho",
        best_epoch=2,
        checkpoint_label="Checkpoint được triển khai",
    )


if __name__ == "__main__":
    main()
