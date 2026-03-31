import streamlit as st
import subprocess
import tempfile
import os
import json

st.title("Secure Genomic PSI — Type 2 Diabetes Risk SNPs")

# -----------------------------
# 1. Converter for raw 23andMe files
# -----------------------------
def convert_23andme_to_vector(raw_bytes, universe_path="snp_universe.json"):
    # Load SNP universe (list of rsIDs)
    with open(universe_path) as f:
        universe = json.load(f)

    # Decode uploaded file
    text = raw_bytes.decode("utf-8", errors="ignore")

    # Parse genotype file
    user_snps = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        rsid, chrom, pos, genotype = parts
        user_snps[rsid] = genotype

    # Build 0/1 vector aligned to universe (presence of SNP)
    vector = [1 if rsid in user_snps else 0 for rsid in universe]

    return vector


# -----------------------------
# 2. Streamlit UI
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload your raw 23andMe genotype file (.txt)",
    type=["txt"]
)

if uploaded_file is not None:
    st.write("### Step 1 — Converting genotype file to SNP vector")

    # Convert uploaded genotype file directly from memory
    raw_bytes = uploaded_file.read()
    vector = convert_23andme_to_vector(raw_bytes)
    st.write("Generated SNP vector:", vector)

    # Create temporary directory for MPC files
    with tempfile.TemporaryDirectory() as tmpdir:
        # This is the ONLY Lab A file used by the backend
        labA_path = os.path.join(tmpdir, "labA.json")

        # Save vector to temporary labA.json
        with open(labA_path, "w") as f:
            json.dump(vector, f)

        # Lab B stays as a fixed file in your project folder
        labB_path = "labB.json"

        st.write("### Step 2 — Running secure PSI protocol")

        # Launch Party 1 (pid=1)
        p1 = subprocess.Popen(
            [
                "py", "-3.11", "psi_genome_intersection.py",
                f"--labA={labA_path}", f"--labB={labB_path}",
                "-M", "2", "-I", "1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Launch Party 0 (pid=0)
        p0 = subprocess.Popen(
            [
                "py", "-3.11", "psi_genome_intersection.py",
                f"--labA={labA_path}", f"--labB={labB_path}",
                "-M", "2", "-I", "0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Collect outputs
        out0, err0 = p0.communicate()
        out1, err1 = p1.communicate()
        
        # Load metadata
        with open("snp_metadata.json") as f:
            metadata = json.load(f)

        # Load SNP universe
        with open("snp_universe.json") as f:
            universe = json.load(f)

        # Determine which SNPs matched (Lab A vector AND Lab B vector)
        matched_snps = []
        for i, rsid in enumerate(universe):
            if vector[i] == 1:  # user has this SNP
                matched_snps.append({
                    "rsID": rsid,
                    "gene": metadata[rsid]["gene"],
                    "condition": metadata[rsid]["condition"],
                    "description": metadata[rsid]["description"]
                })

        # Display results
        st.subheader("Matched Genetic Variants")
        if matched_snps:
            st.table(matched_snps)
        else:
            st.write("No matching variants found.")


        st.write("### Step 3 — Results")

        st.subheader("Party 0 Output")
        st.code(out0)
        if err0:
            st.code(err0)
