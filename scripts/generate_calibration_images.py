#!/usr/bin/env python3
"""
Generate SSM heatmap images from calibration JSON data.

Creates PNG visualizations for CALIBRATION.md showing real deliberative
dialogue patterns used to derive AAP thresholds.

Usage:
    python scripts/generate_calibration_images.py
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def render_ssm_heatmap(
    matrix: list[list[float]],
    title: str,
    output_path: Path,
    pattern: str = "unknown",
    threshold: float = 0.30,
) -> None:
    """Render an SSM matrix as a heatmap PNG."""

    arr = np.array(matrix)
    n = arr.shape[0]

    # Create figure with appropriate size
    fig_size = max(6, n * 0.5)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))

    # Use magma colormap (similar to music SSMs)
    im = ax.imshow(arr, cmap='magma', vmin=0, vmax=1, aspect='equal')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Similarity', rotation=270, labelpad=15)

    # Add threshold line annotation
    ax.text(
        0.02, 0.98, f'Threshold: {threshold}',
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment='top',
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8}
    )

    # Add pattern label
    pattern_colors = {
        'convergent': '#2ecc71',
        'mixed': '#f39c12',
        'transitional': '#3498db',
        'divergent': '#e74c3c',
    }
    pattern_color = pattern_colors.get(pattern, '#95a5a6')
    ax.text(
        0.98, 0.98, pattern.upper(),
        transform=ax.transAxes,
        fontsize=10,
        fontweight='bold',
        verticalalignment='top',
        horizontalalignment='right',
        color=pattern_color,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8}
    )

    # Labels
    ax.set_xlabel('Message Index', fontsize=10)
    ax.set_ylabel('Message Index', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)

    # Tick marks
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(range(n), fontsize=8)
    ax.set_yticklabels(range(n), fontsize=8)

    # Grid for readability
    ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
    ax.grid(which='minor', color='white', linestyle='-', linewidth=0.5, alpha=0.3)

    # Compute and display statistics
    # Get upper triangle (excluding diagonal) for mean similarity
    upper_tri = arr[np.triu_indices(n, k=1)]
    mean_sim = np.mean(upper_tri)
    min_sim = np.min(upper_tri)
    below_threshold = np.sum(upper_tri < threshold)
    total_pairs = len(upper_tri)

    stats_text = f'Mean: {mean_sim:.3f} | Min: {min_sim:.3f} | Below threshold: {below_threshold}/{total_pairs}'
    ax.text(
        0.5, -0.08, stats_text,
        transform=ax.transAxes,
        fontsize=9,
        horizontalalignment='center',
        style='italic'
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"  Saved: {output_path}")
    print(f"    Pattern: {pattern}, Size: {n}x{n}, Mean similarity: {mean_sim:.3f}")


def main():
    """Generate all calibration SSM images."""

    # Paths
    examples_dir = Path("/Users/alexgarden/projects/aap/docs/playground/examples")
    output_dir = Path("/Users/alexgarden/projects/aap/docs/images")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all calibration SSM files
    ssm_files = sorted(examples_dir.glob("calibration-ssm-*.json"))

    if not ssm_files:
        print("No calibration SSM files found!")
        return

    print(f"Found {len(ssm_files)} calibration SSM files\n")

    for ssm_file in ssm_files:
        print(f"Processing: {ssm_file.name}")

        with open(ssm_file) as f:
            data = json.load(f)

        # Extract data
        matrix = data["matrix"]
        description = data.get("description", "Calibration SSM")
        pattern = data.get("pattern", "unknown")

        # Create title from description
        # e.g., "Calibration evidence: Convergent deliberative dialogue"
        title = description.replace("Calibration evidence: ", "")

        # Output filename
        output_name = ssm_file.stem + ".png"
        output_path = output_dir / output_name

        render_ssm_heatmap(
            matrix=matrix,
            title=title,
            output_path=output_path,
            pattern=pattern,
        )

    print(f"\nGenerated {len(ssm_files)} images in {output_dir}")
    print("\nTo embed in CALIBRATION.md:")
    for ssm_file in ssm_files:
        img_name = ssm_file.stem + ".png"
        print(f"  ![{ssm_file.stem}](images/{img_name})")


if __name__ == "__main__":
    main()
