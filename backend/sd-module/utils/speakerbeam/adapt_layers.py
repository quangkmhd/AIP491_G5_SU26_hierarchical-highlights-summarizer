import torch
import torch.nn as nn


def into_tuple(x):
    """
    Convert tensor/list/tuple into tuple type.
    """
    if isinstance(x, list):
        return tuple(x)
    elif isinstance(x, torch.Tensor):
        return (x,)
    elif isinstance(x, tuple):
        return x
    else:
        raise ValueError('x should be tensor, list of tuple')

def into_orig_type(x, orig_type):
    """
    Inverse function of into_tuple (revert to original type).
    """
    if orig_type is tuple:
        return x
    if orig_type is list:
        return list(x)
    if orig_type is torch.Tensor:
        return x[0]
    else:
        assert False


class MulAddAdaptLayer(nn.Module):
    def __init__(self, indim=256, enrolldim=256, ninputs=1, do_addition=False):
        super().__init__()
        self.ninputs = ninputs
        self.do_addition = do_addition

        assert ((do_addition and enrolldim == 2*indim) or \
                (not do_addition and enrolldim == indim))

    def forward(self, main, enroll):
        """
        Parameters:
            main: tensor, tuple hoặc list
                  Activations in the main neural network to be adapted.
                  Tuple/list format is useful when applying adaptation to both 
                  main flow and skip connections simultaneously.
            enroll: tensor, tuple hoặc list
                    Embedding extracted from target speaker enrollment data.
                    Tuple/list format is useful when applying adaptation to both 
                    main flow and skip connections simultaneously.
        """
        assert type(main) == type(enroll)
        orig_type = type(main)
        main, enroll = into_tuple(main), into_tuple(enroll)
        assert len(main) == len(enroll) == self.ninputs

        out = []
        for main0, enroll0 in zip(main, enroll):
            if self.do_addition:
                enroll0_mul, enroll0_add = torch.chunk(enroll0, 2, dim=1)
                out.append(enroll0_mul[...,None] * main0 + enroll0_add[...,None])
            else:
                out.append(enroll0[...,None] * main0)
        return into_orig_type(tuple(out), orig_type)

