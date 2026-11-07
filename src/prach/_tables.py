"""Fixed TS38.211 V15.2.0 §6.3.3; original tables, never current-release Toolbox tables."""
import json
from pathlib import Path

# Table 6.3.3.1-3, transcribed from original PDF page 38; permutation checked on export.
ROOTS_839 = tuple(json.loads(Path(__file__).with_name('_root_table.json').read_text())['roots_839'])
# Tables 6.3.3.1-1/-2: (L_RA, repetitions, CP in Ts at RA mu=0, fixed SCS kHz or None).
FORMATS = {
    '0': (839, 1, 3168, 1.25), '1': (839, 2, 21024, 1.25),
    '2': (839, 4, 4688, 1.25), '3': (839, 4, 3168, 5),
    'A1': (139, 2, 288, None), 'A2': (139, 4, 576, None),
    'A3': (139, 6, 864, None), 'B1': (139, 2, 216, None),
    'B2': (139, 4, 360, None), 'B3': (139, 6, 504, None),
    'B4': (139, 12, 936, None), 'C0': (139, 1, 1240, None),
    'C2': (139, 4, 2048, None),
}
# Tables 6.3.3.1-5/-6/-7: unrestricted sets only, zcz index 0..15.
NCS = {
    1.25: (0,13,15,18,22,26,32,38,46,59,76,93,119,167,279,419),
    5: (0,13,26,33,38,41,49,55,64,76,93,119,139,209,279,419),
    'short': (0,2,4,6,8,10,12,13,15,17,19,23,27,34,46,69),
}
# Table 6.3.3.2-1: (RA SCS kHz, UL SCS kHz) -> (occupied UL RBs, k_bar).
FREQUENCY = {
    (1.25,15):(6,7), (1.25,30):(3,1), (1.25,60):(2,133),
    (5,15):(24,12), (5,30):(12,10), (5,60):(6,7),
    (15,15):(12,2), (15,30):(6,2), (15,60):(3,2),
    (30,15):(24,2), (30,30):(12,2), (30,60):(6,2),
    (60,60):(12,2), (60,120):(6,2),
    (120,60):(24,2), (120,120):(12,2),
}
