"""
Utility functions for handling payment frequency values consistently
"""

from typing import Optional


def normalize_frequency(frequency: Optional[str]) -> Optional[str]:
    """
    Normalize frequency values to uppercase enum format.
    
    Args:
        frequency: The frequency value to normalize (can be any case)
        
    Returns:
        Normalized uppercase frequency value or None if invalid
    """
    if not frequency:
        return None
    
    # Convert to lowercase for comparison
    freq_lower = frequency.lower().strip()
    
    # Map common variations to standard values
    frequency_mapping = {
        'weekly': 'WEEKLY',
        'fortnightly': 'FORTNIGHTLY',
        'four_weekly': 'FOUR_WEEKLY',
        'four weekly': 'FOUR_WEEKLY',
        'monthly': 'MONTHLY',
        'annually': 'ANNUALLY',
        'yearly': 'ANNUALLY',
        'one_off': 'ONE_OFF',
        'one off': 'ONE_OFF',
        'variable': 'ONE_OFF'
    }
    
    return frequency_mapping.get(freq_lower, frequency.upper())


def validate_frequency(frequency: Optional[str]) -> Optional[str]:
    """
    Validate and normalize frequency value.
    
    Args:
        frequency: The frequency value to validate
        
    Returns:
        Valid normalized frequency value or None if invalid
    """
    if not frequency:
        return None
    
    normalized = normalize_frequency(frequency)
    
    # Valid frequency values
    valid_frequencies = ['WEEKLY', 'FORTNIGHTLY', 'FOUR_WEEKLY', 'MONTHLY', 'ANNUALLY', 'ONE_OFF']
    
    if normalized in valid_frequencies:
        return normalized
    
    return None


def get_frequency_multiplier(frequency: Optional[str]) -> float:
    """
    Get the monthly multiplier for a given frequency.
    
    Args:
        frequency: The frequency value
        
    Returns:
        Multiplier to convert to monthly amount
    """
    if not frequency:
        return 1.0
    
    freq_upper = normalize_frequency(frequency)
    
    multipliers = {
        'WEEKLY': 4.33,
        'FORTNIGHTLY': 2.17,
        'FOUR_WEEKLY': 1.08,
        'MONTHLY': 1.0,
        'ANNUALLY': 0.083,
        'ONE_OFF': 0.0
    }
    
    return multipliers.get(freq_upper, 1.0)
