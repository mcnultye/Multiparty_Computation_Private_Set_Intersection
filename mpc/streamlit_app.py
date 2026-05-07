import streamlit as st
import subprocess
import tempfile
import os
import json
import pandas as pd
import re

st.title("Secure Genomic PSI — Genetic Variant Screening")

# ---------------------------------------------------------
# Convert 23andMe file → binary risk vector
# ---------------------------------------------------------
def convert_23andme_to_vector(
    raw_bytes,
    universe_path="snp_universe.json",
    metadata_path="snp_metadata.json"
):
    with open(universe_path) as f:
        universe = json.load(f)

    with open(metadata_path) as f:
        metadata = json.load(f)

    text = raw_bytes.decode("utf-8", errors="ignore")

    user_snps = {}

    for line in text.splitlines():
        if line.startswith("#"):
            continue

        parts = line.strip().split()

        if len(parts) != 4:
            continue

        rsid, chrom, pos, genotype = parts
        user_snps[rsid] = genotype

    vector = []

    for rsid in universe:

        if rsid not in user_snps:
            vector.append(0)
            continue

        genotype = user_snps[rsid]
        risk = metadata[rsid]["risk_allele"]

        vector.append(1 if risk in genotype else 0)

    return vector


# ---------------------------------------------------------
# Upload Section
# ---------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload your raw 23andMe genotype file (.txt)",
    type=["txt"]
)

# ---------------------------------------------------------
# ONLY RUN EVERYTHING AFTER FILE UPLOAD
# ---------------------------------------------------------
if uploaded_file is not None:

    # -----------------------------------------------------
    # Convert uploaded genome to vector
    # -----------------------------------------------------
    raw_bytes = uploaded_file.read()

    vector = convert_23andme_to_vector(raw_bytes)

    # -----------------------------------------------------
    # Create temporary vector file
    # -----------------------------------------------------
    with tempfile.TemporaryDirectory() as tmpdir:

        labA_path = os.path.join(tmpdir, "labA.json")

        with open(labA_path, "w") as f:
            json.dump(vector, f)

        # -------------------------------------------------
        # Main secure PSI comparison
        # -------------------------------------------------
        labB_path = "labB.json"

        # Party 1
        p1 = subprocess.Popen(
            [
                "py",
                "-3.11",
                "psi_genome_intersection.py",
                f"--labA={labA_path}",
                f"--labB={labB_path}",
                "-M",
                "2",
                "-I",
                "1"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Party 0
        p0 = subprocess.Popen(
            [
                "py",
                "-3.11",
                "psi_genome_intersection.py",
                f"--labA={labA_path}",
                f"--labB={labB_path}",
                "-M",
                "2",
                "-I",
                "0"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        out0, err0 = p0.communicate()

        # -------------------------------------------------
        # Extract secure intersection result
        # -------------------------------------------------
        match = re.search(
            r"Secure PSI-cardinality:\s*(\d+)",
            out0
        )

        intersection_size = int(match.group(1)) if match else 0

    # -----------------------------------------------------
    # Success Message
    # -----------------------------------------------------
    st.success("Secure computation completed successfully.")

    # -----------------------------------------------------
    # Load SNP metadata
    # -----------------------------------------------------
    with open("snp_universe.json") as f:
        universe = json.load(f)

    with open("snp_metadata.json") as f:
        metadata = json.load(f)

    # -----------------------------------------------------
    # Build findings categories
    # -----------------------------------------------------
    categories = {}

    for i, rsid in enumerate(universe):

        if vector[i] == 1:

            entry = metadata[rsid]
            cat = entry["category"]

            if cat not in categories:
                categories[cat] = []

            categories[cat].append({
                "rsID": rsid,
                "gene": entry["gene"],
                "condition": entry["condition"],
                "description": entry["description"]
            })

    # -----------------------------------------------------
    # Findings Table
    # -----------------------------------------------------
    st.subheader("Your Genetic Findings")

    if not categories:
        st.info("No matching variants were found.")

    else:
        for cat, items in categories.items():

            st.write(f"### {cat}")

            st.dataframe(
                pd.DataFrame(items),
                use_container_width=True
            )

    # -----------------------------------------------------
    # Summary Metrics
    # -----------------------------------------------------
    st.subheader("Summary Overview")

    total_variants = len(universe)
    risk_variants = sum(vector)

    col1, col2 = st.columns(2)

    col1.metric(
        "Total Variants Screened",
        total_variants
    )

    col2.metric(
        "Risk Variants Found",
        risk_variants
    )

    # -----------------------------------------------------
    # Category Chart
    # -----------------------------------------------------
    category_counts = {
        cat: len(items)
        for cat, items in categories.items()
    }

    if category_counts:

        df_cat = pd.DataFrame({
            "Category": list(category_counts.keys()),
            "Count": list(category_counts.values())
        })

        st.subheader("Risk Variants by Category")

        st.bar_chart(
            df_cat.set_index("Category")
        )

    # -----------------------------------------------------
    # Population Comparison Section
    # -----------------------------------------------------
    st.subheader("Population Comparison")

    st.write(
        "Securely compare your genomic profile against "
        "simulated male and female reference groups."
    )

    gender_reference_map = {
        "Male": "male_reference.json",
        "Female": "female_reference.json"
    }

    comparison_results = {}

    # -----------------------------------------------------
    # Compare against each group
    # -----------------------------------------------------
    for group, ref_path in gender_reference_map.items():

        if not os.path.exists(ref_path):
            st.warning(f"{group} reference file missing.")
            continue

        with tempfile.TemporaryDirectory() as tmpdir:

            labA_path = os.path.join(
                tmpdir,
                "labA.json"
            )

            with open(labA_path, "w") as f:
                json.dump(vector, f)

            # Party 1
            p1 = subprocess.Popen(
                [
                    "py",
                    "-3.11",
                    "psi_genome_intersection.py",
                    f"--labA={labA_path}",
                    f"--labB={ref_path}",
                    "-M",
                    "2",
                    "-I",
                    "1"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Party 0
            p0 = subprocess.Popen(
                [
                    "py",
                    "-3.11",
                    "psi_genome_intersection.py",
                    f"--labA={labA_path}",
                    f"--labB={ref_path}",
                    "-M",
                    "2",
                    "-I",
                    "0"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            out0, err0 = p0.communicate()

            match = re.search(
                r"Secure PSI-cardinality:\s*(\d+)",
                out0
            )

            overlap = int(match.group(1)) if match else 0

            comparison_results[group] = overlap

    # -----------------------------------------------------
    # Population Comparison Chart
    # -----------------------------------------------------
    if comparison_results:

        df_compare = pd.DataFrame({
            "Reference Group": list(comparison_results.keys()),
            "Shared Variants": list(comparison_results.values())
        })

        st.subheader("Shared Variant Overlap")

        st.bar_chart(
            df_compare.set_index("Reference Group")
        )

        # -------------------------------------------------
        # Similarity %
        # -------------------------------------------------
        user_total = sum(vector)

        if user_total > 0:

            similarity = {
                k: (v / user_total) * 100
                for k, v in comparison_results.items()
            }

            col1, col2 = st.columns(2)

            col1.metric(
                "Male Similarity",
                f"{similarity['Male']:.1f}%"
            )

            col2.metric(
                "Female Similarity",
                f"{similarity['Female']:.1f}%"
            )

            best_match = max(
                similarity,
                key=similarity.get
            )

            st.info(
                f"Highest overlap detected with the "
                f"{best_match} reference group."
            )

    # -----------------------------------------------------
    # Proof-of-concept disclaimer
    # -----------------------------------------------------
    st.caption(
        "Reference groups shown are simulated genomic "
        "datasets for proof-of-concept purposes."
    )