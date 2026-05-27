def flag_anomaly(value, mean, std_dev, hard_threshold=None):
    """
    Flag anomalies based on z-score or hard threshold rules.
    """
    if hard_threshold and value > hard_threshold:
        return True
        
    if std_dev == 0 or std_dev is None:
        return False
        
    z_score = abs((value - mean) / std_dev)
    if z_score > 3: # 3 standard deviations
        return True
        
    return False
