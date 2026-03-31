import streamlit as st
import subprocess
import tempfile
import os
import json

st.title("Secure Genomic PSI (Lab A vs Database)")

st.write(
    "Upload Lab A's SNP vector as a JSON array of 0/1. "
    "Lab B is a fixed database stored on the server."
)

# Path to Lab B's fixed database file on disk
FIXED_LAB_B_PATH = "labB_database.json"  # you create this once

uploaded_file = st.file_uploader("Lab A SNP JSON", type=["json"])

if uploaded_file is not None:
    # Save Lab A's upload to a temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        labA_path = os.path.join(tmpdir, "labA.json")
        with open(labA_path, "wb") as f:
            f.write(uploaded_file.read())

        st.write("File uploaded. Running secure PSI protocol...")

        cmd = [
            "python", "-m", "mpyc",
            "psi_genome_intersection.py",
            "-M", "2",
            f"--labA={labA_path}",
            f"--labB={FIXED_LAB_B_PATH}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        st.subheader("Protocol output")
        st.code(result.stdout)

        if result.stderr:
            st.subheader("Errors")
            st.code(result.stderr)
