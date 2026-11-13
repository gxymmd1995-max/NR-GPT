"""FR1 100 MHz / 30 kHz CSI-RS example; figures display only."""

from NRCSIRS_demo import run_case as run_reference_case


def run_case(plot=False):
    return run_reference_case(plot=plot, n_size_grid=273, n_rbs=272)


if __name__ == "__main__":
    print(run_case(plot=True)["channel_estimates"])
