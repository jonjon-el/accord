import numpy as np
import functools

def calc_U (u: float, k: float) -> float:
    """
    Calculate the combined uncertainty.

    Args:
        u (float): The combined standard uncertainty.
        k (float): The coverage factor.

    Returns:
        float: The combined uncertainty.
    """
    return u * k

def calc_u_c (*u_i) -> float:
    """
    Calculate the combined standard uncertainty.

    Args:
        *u_i (float): Variable number of standard uncertainties.
    Returns:
        float: The combined standard uncertainty.
    """
    return functools.reduce(np.hypot, u_i)

def calc_u_A (*measurand_values) -> float:
    """
    Calculate Type A standard uncertainty.

    Args:
        *measurand_values (float): Variable number of the mean values for each series.
    Returns:
        float: The Type A uncertainty.
    """

    n = len(measurand_values)

    # Calculate the sample standard deviation. (n-1 Bessel's correction)
    std_dev = np.std(measurand_values, ddof=1)

    # Calculate the standard uncertainty of the mean
    u_A = std_dev / np.sqrt(n)

    return u_A

def calc_u_B(error_value: float, distribution: str, k: float|None = None) -> float:
    """
    Calculate Type B standard uncertainty.

    Args:
        error_value (float): The value of the error.
        distribution (str): The type of uncertainty. ("rectangular" , "triangular", "normal" distributions are supported)
        k (float): The coverage factor for normal distribution. (ignored for other distributions)
    Returns:
        float: The standard uncertainty.
    """
    
    if distribution == "rectangular":
        u_B = error_value / np.sqrt(3)
    elif distribution == "triangular":
        u_B = error_value / np.sqrt(6)
    elif distribution == "normal":
        if k is None:
            raise ValueError("Coverage factor 'k' is required for normal distribution.")
        if k <= 0:
            raise ValueError("Coverage factor 'k' must be a positive number.")
        u_B = error_value / k
    else:
        raise ValueError("Unsupported distribution type. Supported types are: 'rectangular', 'triangular', 'normal'.")
    
    return u_B