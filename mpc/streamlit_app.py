import streamlit as st
import subprocess
import tempfile
import os
import time

st.title("Secure Genomic PSI (Lab A vs Database)")

uploaded_file = st.file_uploader("Upload Lab A SNP JSON", type=["json"])

# Path to Lab B's fixed database file
FIXED_LAB_B_PATH = "labB.json"

if uploaded_file is not None:
    with tempfile.TemporaryDirectory() as tmpdir:
        labA_path = os.path.join(tmpdir, "labA.json")
        with open(labA_path, "wb") as f:
            f.write(uploaded_file.read())

        st.write("Running secure PSI protocol...")

        # Launch Party 1 (database party)
        p1 = subprocess.Popen(
            ["py", "-3.11", "psi_genome_intersection.py",
             "-M", "2", "-I", "1",
             f"--labA={labA_path}", f"--labB={FIXED_LAB_B_PATH}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Launch Party 0 (user party)
        p0 = subprocess.Popen(
            ["py", "-3.11", "psi_genome_intersection.py",
             "-M", "2", "-I", "0",
             f"--labA={labA_path}", f"--labB={FIXED_LAB_B_PATH}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for Party 0 to finish (it prints the result)
        out0, err0 = p0.communicate()

        st.subheader("Party 0 Output")
        st.code(out0)

        if err0:
            st.subheader("Party 0 Errors")
            st.code(err0)

        # Also show Party 1 output for debugging
        out1, err1 = p1.communicate()

        st.subheader("Party 1 Output")
        st.code(out1)

        if err1:
            st.subheader("Party 1 Errors")
            st.code(err1)
