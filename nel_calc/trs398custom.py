from pylinac.calibration import trs398

class TRS398Custom(trs398.TRS398Photon):
    """Extended class to support ref_temp in the calculation of k_TP and m_corrected."""

    # Anotations for the attributes of the class. These attributes are used in the calculation of k_TP and m_corrected.
    temp: float
    press: float

    def __init__(self, *args, ref_temp: float = 20.0, **kwargs):
        self.ref_temp = ref_temp
        super().__init__(*args, **kwargs)
        
    @property
    def k_tp(self) -> float:
        # print(f"WARNING: Calculating k_TP with temp={self.temp}, press={self.press}, ref_temp={self.ref_temp}")
        # print("The trs398 standard uses a default reference temperature of 20 degrees Celsius for the calculation of k_TP. This custom implementation allows you to specify a different reference temperature if needed.")
        return trs398.k_tp(temp=self.temp, press=self.press, ref_temp=self.ref_temp)