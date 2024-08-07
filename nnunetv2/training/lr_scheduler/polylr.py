from torch.optim.lr_scheduler import _LRScheduler

class PolyLRScheduler(_LRScheduler):
    def __init__(self, optimizer, initial_lr: float, max_steps: int, exponent: float = 0.9, current_step: int = None, eps: float = 1e-6):
        self.optimizer = optimizer
        self.initial_lr = initial_lr
        self.max_steps = max_steps
        self.exponent = exponent
        self.eps = eps
        self.ctr = 0
        super().__init__(optimizer, current_step if current_step is not None else -1, False)

    def step(self, current_step=None):
        if current_step is None or current_step == -1:
            current_step = self.ctr
            self.ctr += 1

        new_lr = self.initial_lr * (max(1/self.max_steps , 1 - current_step / self.max_steps)) ** self.exponent
        # new_lr = self.initial_lr * (1 - current_step / self.max_steps + self.eps) ** self.exponent
        # new_lr = self.initial_lr * (self.eps) ** self.exponent
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = new_lr

class ConstantLRScheduler(_LRScheduler):
    def __init__(self, optimizer, initial_lr: float, max_steps: int, exponent: float = 0.9, current_step: int = None, eps: float =1e-6):
        self.optimizer = optimizer
        self.initial_lr = initial_lr
        self.max_steps = max_steps
        self.exponent = exponent
        self.eps = eps
        self.ctr = 0
        super().__init__(optimizer, current_step if current_step is not None else -1, False)

    def step(self, current_step=None):
        if current_step is None or current_step == -1:
            current_step = self.ctr
            self.ctr += 1

        new_lr = self.initial_lr
        
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = new_lr