# NRRMCode：经典二元Reed–Muller码

这是经典RM(r,m)，不是把NR的(32,K)小块码改名。NR标准小块码仍由NRSmallBlockCode实现，依据TS38.212 V15.2.0 §5.3.3.3、原表5.3.3.3-1；本类不声称其所有参数都对应NR信道。

字段：order为阶数r，整数0..m，默认1；n_variables为变量数m，整数1..10，默认5。__post_init__校验非法范围。n_bits属性K=sum(comb(m,d), d=0..r)，code_length属性N=2^m，均无量纲整数。

monomials()返回单项式变量索引tuple列表：按次数从低到高，同次数字典序，常数项为空tuple。generator()返回int8[K,N]生成矩阵，各列是整数n的低位优先二进制坐标，各行是对应单项式求值。encode(bits)输入整数二进制[K]（拒绝bool），按GF(2)矩阵乘输出int8[N]。

decode(llr)输入有限float[N]，正支持0，负支持1；先硬判决，再按次数从高到低进行子立方奇偶多数投票，同次数统一剥离，输出int8[K]。平票选0，不利用软值幅度，不是软ML；理论最小距离2^(m-r)，错误数≤floor((距离-1)/2)时多数译码可纠正。无CRC/DTX/成功状态，超出纠错半径可能错误。大m、高r的循环成本较高；不承诺实时吞吐。非法形状/值抛ValueError。

```python
from common import NRRMCode
c=NRRMCode(1,5)
b=[0,1,0,1,0,1]
x=c.encode(b)
llr=20*(1-2*x);llr[0]*=-1
assert c.decode(llr).tolist()==b
```

经典RM无3GPP公式表号；MATLAB参考使用独立原生多项式求值，不声称调用不存在的5G Toolbox经典RM函数。
