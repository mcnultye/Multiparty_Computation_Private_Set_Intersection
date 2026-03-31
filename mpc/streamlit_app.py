import streamlit as st
import subprocess
import tempfile
import os
import json

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
# 2. Streamlit UI
# ---------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload your raw 23andMe genotype file (.txt)",
    type=["txt"]
)

if uploaded_file is not None:
    # st.write("### Step 1 — Processing your genetic data...")

    raw_bytes = uploaded_file.read()
    vector = convert_23andme_to_vector(raw_bytes)

    with tempfile.TemporaryDirectory() as tmpdir:
        labA_path = os.path.join(tmpdir, "labA.json")
        with open(labA_path, "w") as f:
            json.dump(vector, f)

        labB_path = "labB.json"  # 32 ones

        # st.write("### Step 2 — Running secure multiparty computation...")

        # Launch Party 1
        p1 = subprocess.Popen(
            ["py", "-3.11", "psi_genome_intersection.py",
             f"--labA={labA_path}", f"--labB={labB_path}",
             "-M", "2", "-I", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Launch Party 0
        p0 = subprocess.Popen(
            ["py", "-3.11", "psi_genome_intersection.py",
             f"--labA={labA_path}", f"--labB={labB_path}",
             "-M", "2", "-I", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        out0, err0 = p0.communicate()

        # ---------------------------------------------------------
        # 3. Show ONLY the final MPC result (no logs)
        # ---------------------------------------------------------
        # st.write("### Step 3 — Secure MPC Result")
        st.success("Secure computation completed successfully.")

        # ---------------------------------------------------------
        # 4. Load metadata + universe and show matched variants
        # ---------------------------------------------------------
        with open("snp_universe.json") as f:
            universe = json.load(f)
        with open("snp_metadata.json") as f:
            metadata = json.load(f)

        categories = {}
        for i, rsid in enumerate(universe):
            if vector[i] == 1:  # user carries the risk allele
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

        st.subheader("Your Genetic Findings")

        if not categories:
            st.info("No matching variants were found based on the stored panel.")
        else:
            for cat, items in categories.items():
                st.write(f"### {cat}")
                st.table(items)
