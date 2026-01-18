"""
Jobs Routes for AutoScraper
Job listing, status, and download endpoints
"""
import os
import csv
import json
from flask import Blueprint, jsonify, request, send_file
from services.job_store import get_all_jobs, get_job, remove_job
from services.checkpoint import list_pending_checkpoints
from config import OUTPUT

# Blueprint for job routes
jobs_bp = Blueprint('jobs', __name__)

OUTPUT_DIR = OUTPUT.get('directory', 'outputs')


@jobs_bp.route('/api/jobs', methods=['GET'])
def list_jobs():
    """
    Get all active jobs.
    
    Returns:
        JSON list of jobs
    """
    jobs = get_all_jobs()
    return jsonify({'jobs': jobs})


@jobs_bp.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Get status of a specific job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON with job details or 404
    """
    job = get_job(job_id)
    if job:
        return jsonify(job)
    return jsonify({'error': 'Job not found'}), 404


@jobs_bp.route('/api/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """
    Remove a job from the list.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON confirmation
    """
    remove_job(job_id)
    return jsonify({'status': 'deleted', 'job_id': job_id})


@jobs_bp.route('/api/checkpoints', methods=['GET'])
def list_checkpoints():
    """
    List all pending checkpoints for resume.
    
    Returns:
        JSON list of checkpoints
    """
    checkpoints = list_pending_checkpoints()
    return jsonify({'checkpoints': checkpoints})


@jobs_bp.route('/api/preview/<job_id>', methods=['GET'])
def preview_data(job_id):
    """
    Preview first 10 rows of a completed job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON with preview data
    """
    job = get_job(job_id)
    
    if not job or not job.get('result_file'):
        return jsonify({'error': 'No data found'}), 404
    
    filename = job['result_file']
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    preview_rows = []
    try:
        if filepath.endswith('.csv'):
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    preview_rows.append(dict(row))
        elif filepath.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                preview_rows = data[:10]
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({
        'total': len(preview_rows),
        'preview': preview_rows
    })


@jobs_bp.route('/download/<filename>')
def download_file(filename):
    """
    Download a result file.
    
    Args:
        filename: Name of file to download
        
    Returns:
        File attachment
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, as_attachment=True)
