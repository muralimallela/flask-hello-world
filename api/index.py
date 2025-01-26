from flask import Flask, request, jsonify, send_file
import os
import yt_dlp
from flask_cors import CORS
import urllib.parse

app = Flask(__name__)
CORS(app)

DOWNLOADS_DIR = 'downloads'

# Function to ensure the downloads directory exists
def ensure_downloads_dir():
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Function to extract video information
def extract_video_info(video_url, list_formats=False):
    ydl_opts = {
        'quiet': True,
        'listformats': list_formats
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(video_url, download=False)

# Function to get available video resolutions and information
def get_available_resolutions(video_url):
    try:
        info_dict = extract_video_info(video_url, list_formats=True)
        formats = info_dict.get('formats', [])
        
        resolutions = {str(f.get('height')) for f in formats if f.get('vcodec') != 'none' and f.get('height')}

        return {
            'success': True,
            'data': {
                'title': info_dict.get('title', ''),
                'thumbnail': info_dict.get('thumbnail', ''),
                'formats': [{'resolution': res, 'label': f'{res}p'} for res in sorted(resolutions, key=int)]
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# API endpoint to get video info
@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    data = request.json
    video_url = data.get('url')
    if not video_url:
        return jsonify({'success': False, 'error': 'URL is required'})
    
    result = get_available_resolutions(video_url)
    return jsonify(result)

# Function to download video or audio
def download_media(video_url, ydl_opts):
    ensure_downloads_dir()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        return ydl.prepare_filename(info)

# API endpoint to download video
@app.route('/api/download-video', methods=['POST'])
def download_video_route():
    data = request.json
    video_url = data.get('url')
    resolution = data.get('resolution')

    if not video_url or not resolution:
        return jsonify({'success': False, 'error': 'URL and resolution are required'})

    ydl_opts = {
        'format': f'bestvideo[height={resolution}]+bestaudio/best[height={resolution}]',
        'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
        'noplaylist': True,
    }

    try:
        filename = download_media(video_url, ydl_opts)
        return jsonify({'success': True, 'data': {'filename': os.path.basename(filename)}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# API endpoint to download audio
@app.route('/api/download-audio', methods=['POST'])
def download_audio_route():
    data = request.json
    video_url = data.get('url')

    if not video_url:
        return jsonify({'success': False, 'error': 'URL is required'})

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
    }

    try:
        filename = download_media(video_url, ydl_opts)
        filename = os.path.splitext(filename)[0] + '.mp3'
        return jsonify({'success': True, 'data': {'filename': os.path.basename(filename)}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# API endpoint to download the file
@app.route('/downloads/<filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOADS_DIR, urllib.parse.unquote(filename))  # Decode the filename
    print(f"File path being accessed: {file_path}")  # Log the file path for debugging

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'success': False, 'error': 'File not found'}), 404

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True, port=5000)
