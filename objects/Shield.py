class Shield:
    def __init__(self, long_range:float, short_range:float, range_distance:float, is_strong_signal:bool) -> None:
        self.long_range = long_range
        self.short_range = short_range
        self.range_distance = range_distance
        self.is_strong_signal = is_strong_signal

    @property
    def get_long_stop(self):
        return self.long_range
    
    @property
    def get_short_stop(self):
        return self.short_range
    
    @property
    def get_signal_strength(self):
        return self.is_strong_signal

    def __repr__(self):
        return f"Shield(LongStop={self.long_range}, ShortStop={self.short_range}, Opt.Distance={self.range_distance}, IsSignal={self.is_strong_signal})"
