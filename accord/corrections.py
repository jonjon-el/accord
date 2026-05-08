from pylinac import ct
from scipy import constants
import numpy as np

def calc_c_T(P_expected_value: float, T_ref: float, P_ref: float) -> float:
    """
    Calculate the sensitivity of temperature.

    Args:
        P_expected_value (float): The expected value of the measurand. (e.g., the expected pressure)
        T_ref (float): The reference temperature.
        P_ref (float): The reference pressure.
    Returns:
        float: The sensitivity of temperature.
    """

    # Check values
    if P_expected_value <= 0:
        raise ValueError("Expected value must be greater than zero.")
    if P_ref <= 0:
        raise ValueError("Reference pressure must be greater than zero.")
    if T_ref <= -constants.zero_Celsius:
        raise ValueError("Reference temperature must be greater than absolute zero.")
    
    # Calculate the sensitivity of temperature
    c_T = abs( P_ref / ((constants.zero_Celsius + T_ref)*P_expected_value))
    return c_T

def calc_c_P(L_expected_value: float, T_expected_value: float, P_expected_value: float, T_ref: float, P_ref: float) -> float:
    """
    Calculate the sensitivity of pressure.

    Args:
        L_expected_value (float): The expected value of the measurand. (e.g., the expected crude lecture)
        T_expected_value (float): The expected value of the measurand. (e.g., the expected temperature)
        P_expected_value (float): The expected value of the measurand. (e.g., the expected pressure)
        T_ref (float): The reference temperature.
        P_ref (float): The reference pressure.
    Returns:
        float: The sensitivity of pressure.
    """

    # Check values
    if T_expected_value <= -constants.zero_Celsius:
        raise ValueError("Expected temperature must be greater than absolute zero.")
    if P_expected_value <= 0:
        raise ValueError("Expected value must be greater than zero.")
    if P_ref <= 0:
        raise ValueError("Reference pressure must be greater than zero.")
    if T_ref <= -constants.zero_Celsius:
        raise ValueError("Reference temperature must be greater than absolute zero.")
    
    # Calculate the sensitivity of pressure
    c_P = abs(((constants.zero_Celsius + T_expected_value)*P_ref*L_expected_value) / ((constants.zero_Celsius + T_ref)*np.power(P_expected_value, 2)))
    return c_P

def calc_c_L(T_expected_value: float, P_expected_value: float, T_ref: float, P_ref: float) -> float:
    """
    Calculate the sensitivity of crude lecture.

    Args:
        T_expected_value (float): The expected value of the measurand. (e.g., the expected temperature)
        P_expected_value (float): The expected value of the measurand. (e.g., the expected pressure)
        T_ref (float): The reference temperature.
        P_ref (float): The reference pressure.
    Returns:
        float: The sensitivity of crude lecture.
    """

    # Check values
    if T_expected_value <= -constants.zero_Celsius:
        raise ValueError("Expected temperature must be greater than absolute zero.")
    if P_expected_value <= 0:
        raise ValueError("Expected value must be greater than zero.")
    if P_ref <= 0:
        raise ValueError("Reference pressure must be greater than zero.")
    if T_ref <= -constants.zero_Celsius:
        raise ValueError("Reference temperature must be greater than absolute zero.")
    
    # Calculate the sensitivity of crude lecture
    c_L = abs(((constants.zero_Celsius + T_expected_value)*P_ref) / ((constants.zero_Celsius + T_ref)*P_expected_value))
    return c_L