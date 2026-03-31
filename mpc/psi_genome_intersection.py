import json
import argparse
from mpyc.runtime import mpc

secint = mpc.SecInt(32)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labA", type=str, default="labA.json")
    parser.add_argument("--labB", type=str, default="labB.json")
    args = parser.parse_args()

    await mpc.start()

    # Decide which file this party reads
    if mpc.pid == 0:
        filename = args.labA
    else:
        filename = args.labB

    with open(filename) as f:
        local_vec = json.load(f)

    local_vec = [int(x) for x in local_vec]
    m = len(local_vec)

    # a from party 0
    if mpc.pid == 0:
        a_futures = [mpc.input(secint(x), senders=0) for x in local_vec]
    else:
        a_futures = [mpc.input(secint(0), senders=0) for _ in range(m)]
    a = await mpc.gather(a_futures)

    # b from party 1
    if mpc.pid == 1:
        b_futures = [mpc.input(secint(x), senders=1) for x in local_vec]
    else:
        b_futures = [mpc.input(secint(0), senders=1) for _ in range(m)]
    b = await mpc.gather(b_futures)

    products = [x * y for x, y in zip(a, b)]
    intersection_size_sec = sum(products)

    intersection_size = await mpc.output(intersection_size_sec)
    print("Secure PSI-cardinality:", intersection_size)

    await mpc.shutdown()

if __name__ == "__main__":
    mpc.run(main())
