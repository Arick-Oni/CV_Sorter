import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def create_plot(title, data, output_path):
    # Set premium styles
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Define models and colors
    models = ["TF-IDF", "model-2 (Zaima)", "modelbest (Moushumi)", "hybrid modelbest 2 + NER", "hybridmodel + NER"]
    colors = ["#475569", "#3b82f6", "#10b981", "#f59e0b", "#ef4444"]
    
    projects = [
        "Net Developer",
        "Remote Dev",
        "Junior Dev",
        "Backend Dev",
        "Software Dev"
    ]
    
    # Calculate positions
    x = np.arange(len(projects))
    width = 0.15
    
    for i, model in enumerate(models):
        accuracies = [data[proj][i] * 100 for proj in projects]
        rects = ax.bar(x + (i - 2) * width, accuracies, width, label=model, color=colors[i], edgecolor='white', linewidth=0.5)
        
        # Add value labels on top of bars
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{int(height)}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8, color='#334155', fontweight='600')
            
    # Premium labeling and details
    ax.set_ylabel('Accuracy (Top 10 Overlap %)', fontsize=12, fontweight='600', color='#1e293b')
    ax.set_title(title, fontsize=15, fontweight='800', color='#0f172a', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(projects, fontsize=11, fontweight='600', color='#1e293b')
    ax.set_ylim(0, 110)
    
    # Legend
    ax.legend(frameon=True, facecolor='white', edgecolor='#e2e8f0', shadow=False, loc='upper right', fontsize=10)
    
    # Custom grids
    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#cbd5e1')
    ax.grid(axis='x', visible=False)
    
    # Remove top/right spines
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color('#cbd5e1')
    ax.spines['bottom'].set_color('#cbd5e1')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Plot saved successfully at {output_path}")

def main():
    # Data definitions (in order: TF-IDF, model-2, modelbest, hybrid modelbest2+ner, hybridmodel+ner)
    ann1_data = {
        "Net Developer": [0.4, 0.4, 0.4, 0.4, 0.4],
        "Remote Dev": [0.2, 0.3, 0.4, 0.4, 0.7],
        "Junior Dev": [0.3, 0.3, 0.3, 0.2, 0.1],
        "Backend Dev": [0.3, 0.4, 0.3, 0.4, 0.4],
        "Software Dev": [0.1, 0.2, 0.3, 0.3, 0.3]
    }

    ann2_data = {
        "Net Developer": [0.4, 0.5, 0.3, 0.3, 0.3],
        "Remote Dev": [0.2, 0.2, 0.2, 0.3, 0.4],
        "Junior Dev": [0.5, 0.5, 0.5, 0.3, 0.4],
        "Backend Dev": [0.4, 0.4, 0.5, 0.4, 0.4],
        "Software Dev": [0.2, 0.3, 0.2, 0.3, 0.2]
    }

    weighted_data = {
        "Net Developer": [0.4, 0.5, 0.3, 0.3, 0.3],
        "Remote Dev": [0.3, 0.3, 0.3, 0.3, 0.2],
        "Junior Dev": [0.5, 0.3, 0.3, 0.2, 0.3],
        "Backend Dev": [0.3, 0.3, 0.4, 0.4, 0.4],
        "Software Dev": [0.3, 0.3, 0.2, 0.3, 0.2]
    }
    
    out_dir = r"c:\Users\arick.sarkar\Desktop\Save The Children Techhub\Fourth Week\CV sorting\cv-platform\resources\Tester"
    
    create_plot(
        "Model Performance Comparison against Annotator 1 (Moushumi)",
        ann1_data,
        f"{out_dir}\\annotator1_comparison.png"
    )
    
    create_plot(
        "Model Performance Comparison against Annotator 2 (Zaima)",
        ann2_data,
        f"{out_dir}\\annotator2_comparison.png"
    )
    
    create_plot(
        "Model Performance Comparison against Weighted Annotator (33.33% Ann1 + 66.67% Ann2)",
        weighted_data,
        f"{out_dir}\\weighted_comparison.png"
    )

if __name__ == "__main__":
    main()
