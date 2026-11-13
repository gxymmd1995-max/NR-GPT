"""FR1 100 MHz / 30 kHz downlink PT-RS example; figures display only."""

from NRDownlinkPTRS_demo import run_case as run_reference_case


def run_case(plot=False):
    return run_reference_case(plot=plot, n_size_grid=273)


if __name__ == "__main__":
    result = run_case(plot=True)
    print("PT-RS symbols:", result["symbols"], "phase_rad:", result["phase_rad"])
