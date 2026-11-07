"""交互绘图无文件输出；阶段过滤、数组快照、分页、轴及关闭时零绘图依赖。"""

import os
from pathlib import Path
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pytest

from cell import NRCell
from diagnostics import NRPlotConfig,NRStagePlotter
from pucch import NRPUCCH0,NRPUCCH0Transmitter,NRPUCCH0Receiver


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close('all')


def test_disabled_does_not_inspect_arrays_import_matplotlib_or_create_files(tmp_path):
    code='''
import sys
from diagnostics import NRStagePlotter
from cell import NRCell
from pucch import NRPUCCH0,NRPUCCH0Transmitter,NRPUCCH0Receiver
p=NRStagePlotter()
p.record('unused',object())
assert p.stages==() and p.figures()==[] and p.show()==[]
r=NRPUCCH0(NRCell(n_size_grid=6))
sent=NRPUCCH0Transmitter(r).transmit([1])
assert NRPUCCH0Receiver(r).receive(sent['waveform'])['harq_ack']==[1]
assert 'matplotlib' not in sys.modules
'''
    env=os.environ.copy();env['PYTHONPATH']=str(Path(__file__).resolve().parents[2]/'src')
    subprocess.run([sys.executable,'-c',code],cwd=tmp_path,env=env,check=True,capture_output=True,text=True)
    assert list(tmp_path.iterdir())==[]


def test_filter_uses_full_stage_prefix_before_array_conversion():
    p=NRStagePlotter(NRPlotConfig(enabled=True,stages=('case1.rx.*',)),prefix='case1')
    p.record('tx.bad',object())
    p.record('rx.metric',[.2,.8],kind='metric')
    assert p.stages==('case1.rx.metric',)
    assert len(p.figures())==1


def test_interactive_show_has_no_save_and_records_are_copied(monkeypatch,tmp_path):
    from matplotlib.figure import Figure
    def forbid_save(*args,**kwargs):raise AssertionError('plot images must never be saved')
    monkeypatch.setattr(Figure,'savefig',forbid_save)
    calls=[];monkeypatch.setattr(plt,'show',lambda **kwargs:calls.append(kwargs))
    p=NRStagePlotter(NRPlotConfig(enabled=True,max_points=16,panels_per_figure=2,max_branches=1))
    wave=np.ones((2,40),complex);p.record('wave',wave);wave[:]=99
    p.record('grid',np.ones((2,3,12)),kind='grid',xlabel='Slot symbol',ylabel='Subcarrier')
    p.record('metrics',[.2,.8],kind='metric',labels=('a','b'))
    figs=p.show(block=True)
    assert len(figs)==2 and calls==[{'block':True}]
    np.testing.assert_array_equal(figs[0].axes[0].lines[0].get_ydata(),np.ones(16))
    assert figs[0].axes[1].get_ylabel()=='Subcarrier'
    assert list(tmp_path.iterdir())==[]


def test_empty_dtx_and_partial_final_page():
    p=NRStagePlotter(NRPlotConfig(enabled=True,panels_per_figure=4))
    p.record('dtx',np.empty(0),kind='sequence')
    p.record('a',[1,2]);p.record('b',[3,4])
    figure=p.figures()[0]
    assert not figure.axes[3].get_visible()
    assert any('DTX' in t.get_text() for t in figure.axes[0].texts)


@pytest.mark.parametrize('values,kwargs',[
    ([1],{'kind':'bad'}),([1],{'kind':'grid'}),(np.zeros((1,0,2)),{'kind':'grid'}),
    ([[1]],{'kind':'metric'}),([float('nan')],{}),([1,2],{'labels':['only_one']})])
def test_stage_axes_and_values_validation(values,kwargs):
    with pytest.raises(ValueError):NRStagePlotter(NRPlotConfig(enabled=True)).record('bad',values,**kwargs)


def test_plotter_constructor_validation():
    with pytest.raises(TypeError):NRStagePlotter(config=True)
    with pytest.raises(TypeError):NRStagePlotter(prefix=1)


def test_actual_tx_rx_intermediates_do_not_change_decisions(monkeypatch):
    monkeypatch.setattr(plt,'show',lambda **kwargs:None)
    r=NRPUCCH0(NRCell(n_size_grid=6),start_symbol=10,n_symbols=2)
    disabled=NRPUCCH0Transmitter(r).transmit([1,0],1)
    config=NRPlotConfig(enabled=True,panels_per_figure=9)
    sent=NRPUCCH0Transmitter(r,plot_config=config).transmit([1,0],1)
    np.testing.assert_array_equal(sent['waveform'],disabled['waveform'])
    assert 'tx.ifft_useful' in sent['plot_stages'] and 'tx.cp_waveform' in sent['plot_stages']
    receiver=NRPUCCH0Receiver(r,2,True,plot_config=config)
    result=receiver.receive(sent['waveform'],cp_fraction=.5)
    assert result['harq_ack']==[1,0] and result['sr']==1
    assert 'rx.fft_windows' in result['plot_stages'] and 'rx.decision' in result['plot_stages']
    assert len(result['plot_stages'])==12
    plotter=NRStagePlotter(config)
    dtx=NRPUCCH0Transmitter(r).transmit((),0,plotter=plotter)
    assert dtx['plot_stages'][0]=='tx.uci_shift' and not dtx['active']
    for cls in (NRPUCCH0Transmitter,NRPUCCH0Receiver):
        with pytest.raises(TypeError):cls(r,plot_config=True)


def test_shared_collector_defers_display_until_whole_chain_is_ready(monkeypatch):
    calls=[];monkeypatch.setattr(plt,'show',lambda **kwargs:calls.append(kwargs))
    r=NRPUCCH0(NRCell(n_size_grid=6),start_symbol=10,n_symbols=2)
    collector=NRStagePlotter(NRPlotConfig(enabled=True),prefix='case0')
    sent=NRPUCCH0Transmitter(r).transmit([1],plotter=collector)
    result=NRPUCCH0Receiver(r).receive(sent['waveform'],plotter=collector)
    assert result['harq_ack']==[1] and calls==[]
    assert collector.stages[0]=='case0.tx.uci_shift'
    assert collector.stages[-1]=='case0.rx.decision'
    assert len(collector.show())==4 and calls==[{'block':False}]


def test_constellation_axes_plot_actual_complex_correlations():
    p=NRStagePlotter(NRPlotConfig(enabled=True))
    data=np.array([[.8+.01j,.79-.01j],[.01+.48j,-.01+.47j]])
    p.record('corr',data,kind='constellation',labels=('S0','S1'),xlabel='I',ylabel='Q')
    ax=p.figures()[0].axes[0]
    np.testing.assert_allclose(ax.collections[0].get_offsets(),np.column_stack((data[0].real,data[0].imag)))
    np.testing.assert_allclose(ax.collections[1].get_offsets(),np.column_stack((data[1].real,data[1].imag)))
    assert ax.get_xlabel()=='I' and ax.get_ylabel()=='Q'
    assert len(ax.texts)==4
    q=NRStagePlotter(NRPlotConfig(enabled=True));q.record('bare',[1j],kind='constellation')
    assert len(q.figures()[0].axes[0].texts)==0


def test_layer_legend_prefix():
    p=NRStagePlotter(NRPlotConfig(enabled=True))
    p.record('layers',[[1j],[-1j]],kind='constellation',branch_prefix='Layer')
    legend=p.figures()[0].axes[0].get_legend()
    assert [text.get_text() for text in legend.get_texts()]==['Layer0','Layer1']
    for invalid in ('',123):
        with pytest.raises(ValueError,match='branch_prefix'):p.record('bad',[1j],kind='constellation',branch_prefix=invalid)
