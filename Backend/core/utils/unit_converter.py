def normalise_unit(unit_str):
    """
    Normalise SAP MEINS codes to canonical units.
    """
    if not unit_str:
        return None
        
    mapping = {
        'L': 'L',
        'KG': 'KG',
        'TO': 'TONNE',
        'GAL': 'GALLON',
        'KWH': 'KWH',
        'KVAH': 'KVAH',
    }
    
    return mapping.get(unit_str.upper(), unit_str.upper())
