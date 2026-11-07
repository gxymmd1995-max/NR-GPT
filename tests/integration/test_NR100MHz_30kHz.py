"""All implemented physical channels at FR1 100MHz/30kHz; no image output."""
import importlib.util
from pathlib import Path
import pytest

CASES=[('pucch','NRPUCCH'+str(i)) for i in range(5)]+[('pusch','NRPUSCH'),('pdsch','NRPDSCH'),('pdcch','NRPDCCH'),('prach','NRPRACH'),('srs','NRSRS')]

@pytest.mark.parametrize('module,name',CASES)
def test_100mhz_time_channel(module,name):
    path=Path(__file__).resolve().parents[2]/'examples'/module/(name+'_100MHz_30kHz_demo.py')
    spec=importlib.util.spec_from_file_location(name+'_100MHz',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    out=m.run_case()
    assert out['passed']
    assert out['n_prbs']==273 and out['scs_khz']==30 and out['n_fft']==4096
    assert out['sample_rate_hz']==122880000
