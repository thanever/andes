"""
Classes for Center of Inertia calculation.
"""
import numpy as np

from andes.core.param import ExtParam
from andes.core.service import NumRepeat, IdxRepeat, BackRef
from andes.core.service import NumReduce, RefFlatten, ExtService
from andes.core.var import ExtState, Algeb, ExtAlgeb
from andes.core.model import ModelData, Model


class COIData(ModelData):
    """COI parameter data"""

    def __init__(self):
        ModelData.__init__(self)


class COIModel(Model):
    """
    Implementation of COI.

    To understand this model, please refer to
    :py:class:`andes.core.service.NumReduce`,
    :py:class:`andes.core.service.NumRepeat`,
    :py:class:`andes.core.service.IdxFlatten`, and
    :py:class:`andes.core.service.BackRef`.
    """
    def __init__(self, system, config):
        Model.__init__(self, system, config)
        self.group = 'Calculation'
        self.flags.update({'tds': True})

        self.SynGen = BackRef(info='Back reference to SynGen idx')

        self.SynGenIdx = RefFlatten(ref=self.SynGen)

        self.M = ExtParam(model='SynGen', src='M',
                          indexer=self.SynGenIdx, export=False,
                          info='Linearly stored SynGen.M',
                          )

        self.wgen = ExtState(model='SynGen',
                             src='omega',
                             indexer=self.SynGenIdx,
                             tex_name=r'\omega_{gen}',
                             info='Linearly stored SynGen.omega',
                             )
        self.agen = ExtState(model='SynGen',
                             src='delta',
                             indexer=self.SynGenIdx,
                             tex_name=r'\delta_{gen}',
                             info='Linearly stored SynGen.delta',
                             )
        self.d0 = ExtService(model='SynGen',
                             src='delta',
                             indexer=self.SynGenIdx,
                             tex_name=r'\delta_{gen,0}',
                             info='Linearly stored initial delta',
                             )
        self.d0avg = NumReduce(u=self.d0,
                               tex_name=r'\delta_{gen,0,avg}',
                               fun=np.average,
                               ref=self.SynGen,
                               info='Average initial delta',
                               )

        self.Mt = NumReduce(u=self.M,
                            tex_name='M_t',
                            fun=np.sum,
                            ref=self.SynGen,
                            info='Summation of M by COI index',
                            )

        self.Mtr = NumRepeat(u=self.Mt,
                             tex_name='M_{tr}',
                             ref=self.SynGen,
                             info='Repeated summation of M',
                             )

        self.pidx = IdxRepeat(u=self.idx, ref=self.SynGen, info='Repeated COI.idx')

        # Note: even if d(omega) /d (omega) = 1, it is still stored as a lambda function.
        # When no SynGen is referencing any COI, j_update will not be called,
        # and Jacobian will become singular. `diag_ep1e-6` needs to be used.

        self.omega = Algeb(tex_name=r'\omega_{coi}',
                           info='COI speed',
                           v_str='1',
                           v_setter=True,
                           e_str='-omega',
                           diag_eps=1e-6,
                           )
        self.delta = Algeb(tex_name=r'\delta_{coi}',
                           info='COI rotor angle',
                           v_str='d0avg',
                           v_setter=True,
                           e_str='-delta',
                           diag_eps=1e-6,
                           )

        # Note:
        # `omega_sub` or `delta_sub` must not provide `v_str`.
        # Otherwise, values will be incorrectly summed for `omega` and `delta`.
        self.omega_sub = ExtAlgeb(model='COI',
                                  src='omega',
                                  e_str='M * wgen / Mtr',
                                  indexer=self.pidx,
                                  info='COI frequency contribution of each generator'
                                  )
        self.delta_sub = ExtAlgeb(model='COI',
                                  src='delta',
                                  e_str='M * agen / Mtr',
                                  indexer=self.pidx,
                                  info='COI angle contribution of each generator'
                                  )

    def set_in_use(self):
        """
        Set the ``Model.in_use`` flag based on ``len(self.SynGenIdx.v)``.
        """
        self.in_use = (len(self.SynGenIdx.v) > 0)


class COI(COIData, COIModel):
    """
    Center of inertia calculation class.
    """

    def __init__(self, system, config):
        COIData.__init__(self)
        COIModel.__init__(self, system, config)
