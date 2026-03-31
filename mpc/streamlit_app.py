import streamlit as st
import subprocess
import tempfile
import os
import json

st.title("Secure Genomic PSI — Rare Variant Screening")

# -----------------------------
# 1. Converter
# -----------------------------
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


# -----------------------------
# 2. Streamlit UI
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload your raw 23andMe genotype file (.txt)",
    type=["txt"]
)

if uploaded_file is not None:
    st.write("### Step 1 — Converting genotype file to risk vector")

    raw_bytes = uploaded_file.read()
    vector = convert_23andme_to_vector(raw_bytes)
    st.write("Risk vector:", vector)

    with tempfile.TemporaryDirectory() as tmpdir:
        labA_path = os.path.join(tmpdir, "labA.json")
        with open(labA_path, "w") as f:
            json.dump(vector, f)

        labB_path = "labB.json"  # 20 ones

        st.write("### Step 2 — Running secure MPC")

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

        out0, err0 = p0.communicate()

        st.write("### Step 3 — Secure MPC Result")
        st.code(out0)

        # -----------------------------
        # Show matched variants
        # -----------------------------
        with open("snp_universe.json") as f:
            universe = json.load(f)
        with open("snp_metadata.json") as f:
            metadata = json.load(f)

        matched = []
        for i, rsid in enumerate(universe):
            if vector[i] == 1:
                matched.append({
                    "rsID": rsid,
                    "gene": metadata[rsid]["gene"],
                    "condition": metadata[rsid]["condition"],
                    "description": metadata[rsid]["description"]
                })

        st.subheader("Matched Pathogenic Variants")
        if matched:
            st.table(matched)
        else:
            st.write("No pathogenic variants detected.")
