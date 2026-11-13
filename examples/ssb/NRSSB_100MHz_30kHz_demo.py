"""FR1 100MHz/30kHz carrier with one 20RB SS/PBCH block; display only."""

from NRSSB_demo import main
from diagnostics import ExampleLogger, NRPlotConfig


def run_case(log, plot=False):
    return main(
        log, plot_config=NRPlotConfig(enabled=plot, channel="SSB"), n_size_grid=273
    )


if __name__ == "__main__":
    with ExampleLogger(__file__) as log:
        run_case(log, plot=True)
    import matplotlib.pyplot as plt

    plt.show()
