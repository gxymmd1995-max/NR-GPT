"""FR1 100MHz/30kHz carrier with one 20RB SS/PBCH block; display only."""
from NRSSB_demo import main
from diagnostics import ExampleLogger

if __name__=='__main__':
    with ExampleLogger(__file__) as log:main(log,n_size_grid=273)
    import matplotlib.pyplot as plt
    plt.show()
