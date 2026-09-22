"""Plot statistics of the curated studies."""

import json
from itertools import accumulate
from pathlib import Path

import matplotlib.pyplot as plt

# 1. Load the JSON data
data_dir: Path = Path(__file__).parent
output_dir: Path = Path(__file__).parent
identifiers_path: Path = data_dir / "study_identifiers.json"
with open(identifiers_path) as file:
    data = json.load(file)

# ------------ Cumulative plot ---------------

# Extract years and count studies per year
studies_per_year = {}
for _study_id, study_info in data.items():
    year = study_info[1][0:4]
    if year not in studies_per_year:
        studies_per_year[year] = 1
    else:
        studies_per_year[year] += 1

# Sort the keys (years) as integers to ensure chronological order
years = sorted(studies_per_year.keys(), key=int)
counts = [studies_per_year[year] for year in years]
cumulative_counts = list(accumulate(counts))

# Label the last point
last_year = years[-1]
last_value = cumulative_counts[-1]

# 3. Create the plot
fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(years, cumulative_counts, linestyle="-", color="#1E40AF", linewidth=4, zorder=3)
ax.bar(years, cumulative_counts, color="#5A7BE9", alpha=0.2, linewidth=1, zorder=2)
# ax.fill_between(years, cumulative_counts, color='#3B82F6', alpha=0.1)
# Plot ONLY the last point as a marker
ax.plot(
    years[-1:],
    cumulative_counts[-1:],
    marker="o",
    markersize=11,
    color="darkorange",
    linestyle="None",
    zorder=4,
)
ax.text(
    last_year,
    last_value + 10,
    f" Total: {last_value}",
    verticalalignment="bottom",
    fontweight="bold",
    fontsize=16,
)

# 4. Refine formatting for time-series data
ax.set_title("Total studies to date", fontsize=18)
ax.set_xlabel("Year", fontsize=18)
ax.set_ylabel("Number of studies", fontsize=18)
ax.set_xticks(years)  # Ensures every year is shown on the x-axis
ax.grid(axis="y", linestyle="-", alpha=0.3)
ax.tick_params(axis="both", labelsize=12)
# ax.legend(loc='best', frameon=False, fontsize=18)

# Hide all four borders (spines)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(left=False, bottom=False, labelleft=True, labelbottom=True)

fig.show()
fig.savefig(output_dir / "pkdb_cumulative_studies.png", dpi=300, bbox_inches="tight")

# ------------ Cumulative amount of medications ---------------
# Extract years and count studies per year
medications_per_year = {}
drugs = []
for _study_id, study_info in data.items():
    year = study_info[1][0:4]
    drug = study_info[0].split("/")[0]
    if drug not in drugs:
        if year not in medications_per_year:
            medications_per_year[year] = 1
        else:
            medications_per_year[year] += 1
        drugs.append(drug)

# Sort the keys (years) as integers to ensure chronological order
years = sorted(medications_per_year.keys(), key=int)
counts = [medications_per_year[year] for year in years]
cumulative_counts = list(accumulate(counts))

# Label the last point
last_year = years[-1]
last_value = cumulative_counts[-1]

# 3. Create the plot
fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(years, cumulative_counts, linestyle="-", color="#1E40AF", linewidth=4, zorder=3)
ax.bar(years, cumulative_counts, color="#5A7BE9", alpha=0.2, linewidth=1, zorder=2)
# ax.fill_between(years, cumulative_counts, color='#3B82F6', alpha=0.1)
# Plot ONLY the last point as a marker
ax.plot(
    years[-1:],
    cumulative_counts[-1:],
    marker="o",
    markersize=11,
    color="darkorange",
    linestyle="None",
    zorder=4,
)
ax.text(
    last_year,
    last_value,
    f" Total: {last_value}",
    verticalalignment="bottom",
    fontweight="bold",
    fontsize=16,
)

# 4. Refine formatting for time-series data
ax.set_title("Total medications to date", fontsize=18)
ax.set_xlabel("Year", fontsize=18)
ax.set_ylabel("Number of medications", fontsize=18)
ax.set_xticks(years)  # Ensures every year is shown on the x-axis
ax.grid(axis="y", linestyle="-", alpha=0.3)
ax.tick_params(axis="both", labelsize=12)
# ax.legend(loc='best', frameon=False, fontsize=18)

# Hide all four borders (spines)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(left=False, bottom=False, labelleft=True, labelbottom=True)

fig.show()
fig.savefig(
    output_dir / "pkdb_cumulative_medications.png", dpi=300, bbox_inches="tight"
)

# ------------ Top 20 drugs ---------------

# Extract drugs and count their studies
studies_per_medication = {}
for _study_id, study_info in data.items():
    drug = study_info[0].split("/")[0]
    if drug not in studies_per_medication:
        studies_per_medication[drug] = 1
    else:
        studies_per_medication[drug] += 1

# Sort drugs
sorted_medications = dict(
    sorted(studies_per_medication.items(), key=lambda x: x[1], reverse=False)
)
medications = list(sorted_medications)
counts = [sorted_medications[medication] for medication in sorted_medications]

# Create the plot
fig, ax = plt.subplots(figsize=(4, 15))
ax.barh(
    medications, counts, color="#5A7BE9", linewidth=1, zorder=2, edgecolor="#1E40AF"
)
# Add numbers to each bar
# ax.containers contains the bars, and we iterate through them
for bar in ax.containers[0]:
    width = bar.get_width()
    ax.text(
        width + 2,  # X position: slightly to the right of the bar
        bar.get_y() + bar.get_height() / 2,  # Y position: centered vertically
        f"{width}",  # The count
        va="center",  # Vertical alignment
        fontsize=12,
        color="#1E40AF",
    )

# Hide all four borders (spines)
for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(left=False, bottom=False, labelleft=True, labelbottom=True)

ax.grid(axis="x", linestyle="-", alpha=0.3, zorder=1)
ax.tick_params(axis="both", labelsize=12)
ax.set_xlabel("Number of studies", fontsize=18)
fig.show()
fig.savefig(output_dir / "pkdb_medications.png", dpi=300, bbox_inches="tight")
