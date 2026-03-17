from mpyc.runtime import mpc

# secure integer type (32)
secint = mpc.SecInt(32)

async def main():
    import json

    await mpc.start()

    # Party 0 = Lab A and Party 1 = Lab B
    if mpc.pid == 0: # party ID
        filename = "labA.json"
    else:
        filename = "labB.json"

    with open(filename) as f:
        local_vec = json.load(f)

    # Ensure entries are 0 or 1 ints
    local_vec = [int(x) for x in local_vec]
    m = len(local_vec)

    # Secret-share local vector 
    local_sec = [secint(x) for x in local_vec]

    # a comes from party 0 (Lab A)
    if mpc.pid == 0:
        a_inputs = local_sec
    else:
        a_inputs = [secint(0)] * m  # dummy values for lab B

    a = [await mpc.input(x, senders=0) for x in a_inputs]

    # b comes from party 1 (Lab B)
    if mpc.pid == 1:
        b_inputs = local_sec
    else:
        b_inputs = [secint(0)] * m  # dummy values for Lab A

    b = [await mpc.input(x, senders=1) for x in b_inputs]

    # Secure inner product
    products = [x * y for x, y in zip(a, b)] 
    intersection_size_sec = mpc.sum(products)

    # Reveal only the final output
    intersection_size = await mpc.output(intersection_size_sec)

    # Print result
    if mpc.pid == 0:
        print("Secure PSI-cardinality (|S_A ∩ S_B|):", intersection_size)

    await mpc.shutdown()

if __name__ == "__main__":
    mpc.run(main())
