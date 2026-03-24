from mpyc.runtime import mpc

# secure integer type (32 bits)
secint = mpc.SecInt(32)

async def main():
    import json

    await mpc.start()

    # Party 0 = Lab A, Party 1 = Lab B
    if mpc.pid == 0:
        filename = "labA.json"
    else:
        filename = "labB.json"

    # Load local SNP vector (0/1 values)
    with open(filename) as f:
        local_vec = json.load(f)

    # Ensure entries are ints
    local_vec = [int(x) for x in local_vec]
    m = len(local_vec)


    # a comes from party 0 (Lab A)
    if mpc.pid == 0:
        a_futures = [mpc.input(secint(x), senders=0) for x in local_vec]
    else:
        a_futures = [mpc.input(secint(0), senders=0) for _ in range(m)]

    a = await mpc.gather(a_futures)

    # b comes from party 1 (Lab B)
    if mpc.pid == 1:
        b_futures = [mpc.input(secint(x), senders=1) for x in local_vec]
    else:
        b_futures = [mpc.input(secint(0), senders=1) for _ in range(m)]

    b = await mpc.gather(b_futures)


    products = [x * y for x, y in zip(a, b)]
    intersection_size_sec = sum(products)

    # Reveal only the final scalar
    intersection_size = await mpc.output(intersection_size_sec)

    print("Secure PSI-cardinality (|S_A ∩ S_B|):", intersection_size)

    await mpc.shutdown()

if __name__ == "__main__":
    mpc.run(main())
