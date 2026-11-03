"""绘图字段、阶段通配符配置及可显示容量边界。"""

import pytest

from diagnostics import NRPlotConfig


def test_disabled_default_and_explicit_stage_selection():
    assert not NRPlotConfig().enabled
    config=NRPlotConfig(enabled=True,stages=('case0.tx.*','case0.rx.*'),max_points=32,panels_per_figure=3,max_branches=2)
    assert config.stages==('case0.tx.*','case0.rx.*') and config.panels_per_figure==3
    assert NRPlotConfig(stages=()).stages==()


@pytest.mark.parametrize('kwargs,error',[
    ({'enabled':1},TypeError),({'stages':[]},ValueError),({'stages':('',)},ValueError),
    ({'stages':(None,)},ValueError),({'max_points':True},TypeError),({'max_points':15},ValueError),
    ({'panels_per_figure':0},ValueError),({'panels_per_figure':10},ValueError),
    ({'max_branches':0},ValueError),({'channel':''},ValueError),({'channel':None},ValueError)])
def test_invalid_plot_configuration(kwargs,error):
    with pytest.raises(error):NRPlotConfig(**kwargs)
