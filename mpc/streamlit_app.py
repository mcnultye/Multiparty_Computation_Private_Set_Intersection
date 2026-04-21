import streamlit as st
import subprocess
import tempfile
import os
import json
import pandas as pd
import re

st.title("Secure Genomic PSI — Genetic Variant Screening")

# ---------------------------------------------------------
# 1. Convert 23andMe file → risk-aware vector
# ---------------------------------------------------------
def convert_23andme_to_vector(raw_bytes, universe_path="snp_universe.json", metadata_path="snp_metadata.json"):
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
# UI Upload
# ---------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload your raw 23andMe genotype file (.txt)",
    type=["txt"]
)

if uploaded_file is not None:
    raw_bytes = uploaded_file.read()
    vector = convert_23andme_to_vector(raw_bytes)

    # Reference files
    age_reference_map = {
        "18-30": "18_30_reference.json",
        "30-50": "30_50_reference.json",
        "50+": "50plus_reference.json"
    }

    # Tabs
    tab1, tab2 = st.tabs(["Your Results", "Age Comparison"])

    # =====================================================
    # TAB 1 — ORIGINAL RESULTS
    # =====================================================
    with tab1:
        with tempfile.TemporaryDirectory() as tmpdir:
            labA_path = os.path.join(tmpdir, "labA.json")
            with open(labA_path, "w") as f:
                json.dump(vector, f)

            labB_path = "labB.json"

            # Run MPC
            p1 = subprocess.Popen(
                ["py", "-3.11", "psi_genome_intersection.py",
                 f"--labA={labA_path}", f"--labB={labB_path}",
                 "-M", "2", "-I", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            p0 = subprocess.Popen(
                ["py", "-3.11", "psi_genome_intersection.py",
                 f"--labA={labA_path}", f"--labB={labB_path}",
                 "-M", "2", "-I", "0"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            out0, _ = p0.communicate()

            # Extract intersection
            match = re.search(r"Secure PSI-cardinality:\s*(\d+)", out0)
            intersection_size = int(match.group(1)) if match else 0

        st.success("Secure computation completed successfully.")

        # Load metadata
        with open("snp_universe.json") as f:
            universe = json.load(f)
        with open("snp_metadata.json") as f:
            metadata = json.load(f)

        # Build categories
        categories = {}
        for i, rsid in enumerate(universe):
            if vector[i] == 1:
                entry = metadata[rsid]
                cat = entry["category"]
                categories.setdefault(cat, []).append({
                    "rsID": rsid,
                    "gene": entry["gene"],
                    "condition": entry["condition"],
                    "description": entry["description"]
                })

        # ---------------- Findings ----------------
        st.subheader("Your Genetic Findings")

        if not categories:
            st.info("No matching variants were found.")
        else:
            for cat, items in categories.items():
                with st.expander(f"{cat} ({len(items)})"):
                    st.dataframe(pd.DataFrame(items), use_container_width=True)

        # ---------------- Summary ----------------
        st.subheader("Summary Overview")

        total_variants = len(universe)
        risk_variants = sum(vector)

        col1, col2 = st.columns(2)
        col1.metric("Total Variants", total_variants)
        col2.metric("Risk Variants", risk_variants)

        # ---------------- Category Chart ----------------
        category_counts = {cat: len(items) for cat, items in categories.items()}

        if category_counts:
            df_cat = pd.DataFrame({
                "Category": list(category_counts.keys()),
                "Count": list(category_counts.values())
            })

            st.subheader("Risk Variants by Category")
            st.bar_chart(df_cat.set_index("Category"))

        # ---------------- Overlap Chart ----------------
        st.subheader("User vs Reference Panel Overlap")

        overlap_df = pd.DataFrame({
            "Type": ["User Only", "Shared", "Reference Only"],
            "Count": [
                max(risk_variants - intersection_size, 0),
                intersection_size,
                max(len(vector) - risk_variants, 0)
            ]
        })

        st.bar_chart(overlap_df.set_index("Type"))

    # =====================================================
    # TAB 2 — AGE COMPARISON (WITH DROPDOWN)
    # =====================================================
    with tab2:
        st.subheader("Age-Based Comparison")

        # Dropdown ONLY here
        age_option = st.selectbox(
            "Select your age group",
            ["18-30", "30-50", "50+"]
        )

        user_group = age_option

        st.write(f"Comparing your genome to the **{user_group} age group**.")

        results = {}

        for group, ref_path in age_reference_map.items():
            if not os.path.exists(ref_path):
                st.warning(f"{group} reference file missing.")
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                labA_path = os.path.join(tmpdir, "labA.json")
                with open(labA_path, "w") as f:
                    json.dump(vector, f)

                p1 = subprocess.Popen(
                    ["py", "-3.11", "psi_genome_intersection.py",
                     f"--labA={labA_path}", f"--labB={ref_path}",
                     "-M", "2", "-I", "1"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                p0 = subprocess.Popen(
                    ["py", "-3.11", "psi_genome_intersection.py",
                     f"--labA={labA_path}", f"--labB={ref_path}",
                     "-M", "2", "-I", "0"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                out0, _ = p0.communicate()

                match = re.search(r"Secure PSI-cardinality:\s*(\d+)", out0)
                intersection_size = int(match.group(1)) if match else 0

                results[group] = intersection_size

        # ---------------- Chart ----------------
        if results:
            df = pd.DataFrame({
                "Age Group": list(results.keys()),
                "Overlap": list(results.values())
            })

            st.subheader("Overlap Across Age Groups")
            st.bar_chart(df.set_index("Age Group"))

            # ---------------- % similarity ----------------
            user_total = sum(vector)

            if user_total > 0:
                similarity = {
                    k: (v / user_total) * 100 for k, v in results.items()
                }

                best_group = max(similarity, key=similarity.get)

                st.metric(
                    "Similarity to Selected Age Group",
                    f"{similarity[user_group]:.1f}%"
                )

                if best_group == user_group:
                    st.success("Your genetic profile aligns most with this age group.")
                else:
                    st.warning(f"You align more with the {best_group} group.")
        else:
            st.info("No reference data available.")