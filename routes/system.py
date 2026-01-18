"""
System Routes for AutoScraper
Health check, logs, and rate limit status endpoints
"""
import time
from flask import Blueprint, jsonify
from utils.logging_setup import get_recent_logs
from config import RATE_LIMIT
import scraper_selenium

# Blueprint for system routes
system_bp = Blueprint('system', __name__)

# Rate limit tracking
REQUEST_TIMESTAMPS = []


def track_request():
    """Track a request for rate limiting meter."""
    REQUEST_TIMESTAMPS.append(time.time())
    # Keep only last 60 seconds
    cutoff = time.time() - 60
    while REQUEST_TIMESTAMPS and REQUEST_TIMESTAMPS[0] < cutoff:
        REQUEST_TIMESTAMPS.pop(0)


def get_rate_status():
    """
    Get current rate limit status.
    
    Returns:
        dict: Rate status with level (COOL/WARM/HOT), rpm, and percentage
    """
    cutoff = time.time() - 60
    recent = [t for t in REQUEST_TIMESTAMPS if t > cutoff]
    rpm = len(recent)
    
    max_rpm = RATE_LIMIT.get('max_requests_per_minute', 30)
    warning = RATE_LIMIT.get('warning_threshold', 20)
    danger = RATE_LIMIT.get('danger_threshold', 25)
    
    if rpm >= danger:
        level = 'HOT'
    elif rpm >= warning:
        level = 'WARM'
    else:
        level = 'COOL'
    
    return {
        'level': level,
        'rpm': rpm,
        'max_rpm': max_rpm,
        'percentage': min(100, (rpm / max_rpm) * 100)
    }


@system_bp.route('/api/health', methods=['GET'])
def health_check():
    """
    Check system and account health.
    
    Returns:
        JSON with health status
    """
    try:
        result = scraper_selenium.check_account_health()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'recommendation': 'Health check failed. Check your setup.'
        }), 500


@system_bp.route('/api/logs', methods=['GET'])
def get_logs():
    """
    Get recent log entries for UI display.
    
    Returns:
        JSON with log entries
    """
    logs = get_recent_logs(50)
    return jsonify({'logs': logs})


@system_bp.route('/api/rate-status', methods=['GET'])
def rate_status():
    """
    Get current rate limit status.
    
    Returns:
        JSON with rate limit info
    """
    return jsonify(get_rate_status())
