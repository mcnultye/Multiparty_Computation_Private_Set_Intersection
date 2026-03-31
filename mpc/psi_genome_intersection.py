import json
import argparse
from mpyc.runtime import mpc

secint = mpc.SecInt(32)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labA", type=str, required=True)
    parser.add_argument("--labB", type=str, required=True)
    args = parser.parse_args()

    await mpc.start()

    # Everyone loads both vectors from the paths passed in
    with open(args.labA) as f:
        vecA = json.load(f)
    with open(args.labB) as f:
        vecB = json.load(f)

    vecA = [int(x) for x in vecA]
    vecB = [int(x) for x in vecB]

    assert len(vecA) == len(vecB), "Lab A and Lab B vectors must be same length"
    m = len(vecA)

    # Party 0 inputs vecA, Party 1 inputs zeros
    if mpc.pid == 0:
        a_futures = [mpc.input(secint(x), senders=0) for x in vecA]
    else:
        a_futures = [mpc.input(secint(0), senders=0) for _ in range(m)]
    a = await mpc.gather(a_futures)

    # Party 1 inputs vecB, Party 0 inputs zeros
    if mpc.pid == 1:
        b_futures = [mpc.input(secint(x), senders=1) for x in vecB]
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
