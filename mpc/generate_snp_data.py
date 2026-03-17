import json
import random

def generate_snp_vector(m, p_mut, base=None, corr=None):
    """
    m: length of SNP vector
    p_mut: base mutation probability
    base: optional base vector to correlate with
    corr: if not None, probability of copying base's bit instead of sampling fresh
    """
    vec = []
    for i in range(m):
        if base is not None and corr is not None:
            if random.random() < corr:
                vec.append(base[i])
                continue
        # fresh sample
        bit = 1 if random.random() < p_mut else 0
        vec.append(bit)
    return vec

def main():
    random.seed(42)

    # Parameters
    m = 10000          # number of SNP positions
    p_mut = 0.01       # mutation probability
    corr = 0.5         # correlation between labs (0 = independent, 1 = identical)

    # Generate Lab A vector
    labA = generate_snp_vector(m, p_mut)

    # Generate Lab B vector, partially correlated with Lab A
    labB = generate_snp_vector(m, p_mut, base=labA, corr=corr)

    # Save to JSON files
    with open("labA.json", "w") as f:
        json.dump(labA, f)

    with open("labB.json", "w") as f:
        json.dump(labB, f)

    print(f"Generated labA.json and labB.json with m={m}, p_mut={p_mut}, corr={corr}")

if __name__ == "__main__":
    main()
