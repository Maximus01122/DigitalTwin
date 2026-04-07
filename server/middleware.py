class DataPreprocessingFE:
    """Applies a digital low-pass filter (EWMA) to smooth 1-Wire temperature readings."""
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.filtered_t = None
        
    def process(self, raw_temperature):
        if self.filtered_t is None:
            self.filtered_t = raw_temperature
        else:
            self.filtered_t = (self.alpha * raw_temperature) + ((1 - self.alpha) * self.filtered_t)
            
        return self.filtered_t
