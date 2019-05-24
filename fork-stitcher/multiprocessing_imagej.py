import imagej
from multiprocessing import Pool

def f(x):
    # ij = imagej.init('/Applications/Fiji.app')
    print(x)

# ij = imagej.init('/Applications/Fiji.app')

with Pool(processes=2) as pool:
    for i in range(10):
        pool.apply_async(f, args=(i,))

    pool.close()
    pool.join()