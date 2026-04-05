bl_info = {
    "name": "Blender Cloud Storage",
    "author": "Kashish aka MrKuros",
    "version": (3, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Cloud",
    "description": "Upload and download Blender files with dependencies to AWS S3 and Google Drive",
    "category": "Development",
    "doc_url": "https://github.com/mrkuros/bloc",
    "tracker_url": "https://github.com/mrkuros/bloc/issues",
}

import bpy
import os
import sys
import shutil
import tempfile
import logging
import subprocess
import pickle
import platform

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Platform detection
PLATFORM = platform.system()  # 'Windows', 'Darwin' (macOS), or 'Linux'
logger.info(f"Platform: {PLATFORM}")

# Blender version info
BLENDER_VERSION = bpy.app.version
BLENDER_VERSION_STRING = f"{BLENDER_VERSION[0]}.{BLENDER_VERSION[1]}.{BLENDER_VERSION[2]}"
logger.info(f"Blender Cloud Storage v3.0 loading on Blender {BLENDER_VERSION_STRING}")

# Package requirements
REQUIRED_PACKAGES = [
    "google-auth==2.35.0",
    "google-auth-httplib2==0.2.0",
    "google-auth-oauthlib==1.2.0",
    "google-api-python-client==2.147.0",
    "boto3"
]

# Google Drive API scope
# Using 'drive' scope to see ALL your Drive files (including existing ones)
# 'drive.file' would only show files created by this app
SCOPES = ['https://www.googleapis.com/auth/drive']

# Global state
s3_client = None
drive_service = None
packages_installed = False

def get_modules_path():
    """Get Blender modules path."""
    modules_path = bpy.utils.user_resource("SCRIPTS", path="modules", create=True)
    logger.info(f"Modules path: {modules_path}")
    return modules_path

def get_credentials_path():
    """Get path for storing credentials."""
    scripts_path = bpy.utils.user_resource("SCRIPTS", create=True)
    creds_dir = os.path.join(scripts_path, "addons", "cloud_storage_data")
    os.makedirs(creds_dir, exist_ok=True)
    return creds_dir

def get_install_flag_path():
    """Get path for package installation flag."""
    return os.path.join(get_credentials_path(), ".packages_v3")

def are_packages_installed():
    """Check if packages are already installed."""
    return os.path.exists(get_install_flag_path())

def mark_packages_installed():
    """Mark packages as installed."""
    with open(get_install_flag_path(), 'w') as f:
        f.write("v3.0")

def _run_pip_check():
    """Check if pip is available via sys.executable."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True, text=True
    )
    return result.returncode == 0

def ensure_pip():
    """Ensure pip is available, trying multiple methods.
    
    Works across all platforms and Python configurations:
    - Blender's bundled Python (all versions)
    - System Python on Linux/macOS/Windows
    - Python installs without pip or ensurepip wheels
    """
    # Method 1: pip already available
    try:
        if _run_pip_check():
            logger.info("✓ pip is available")
            return True
    except Exception:
        pass
    
    # Method 2: ensurepip (standard library, but may lack bundled wheel on some distros)
    logger.info("pip not found — trying ensurepip...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ensurepip", "--upgrade"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and _run_pip_check():
            logger.info("✓ pip installed via ensurepip")
            return True
        else:
            logger.warning(f"ensurepip did not succeed: {result.stderr.strip()}")
    except Exception as e:
        logger.warning(f"ensurepip not available: {e}")
    
    # Method 3: Download get-pip.py (works when ensurepip is broken/missing)
    logger.info("Trying to download get-pip.py from bootstrap.pypa.io...")
    try:
        import urllib.request
        get_pip_path = os.path.join(tempfile.gettempdir(), "get-pip.py")
        urllib.request.urlretrieve(
            "https://bootstrap.pypa.io/get-pip.py",
            get_pip_path
        )
        
        # Try without --break-system-packages first, then with it (PEP 668 / Debian)
        for extra_args in [[], ["--break-system-packages"]]:
            cmd = [sys.executable, get_pip_path] + extra_args
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and _run_pip_check():
                logger.info("✓ pip installed via get-pip.py")
                return True
        
        logger.warning(f"get-pip.py failed: {result.stderr.strip()}")
    except Exception as e:
        logger.warning(f"get-pip.py download/install failed: {e}")
    
    logger.error("All methods to install pip have failed")
    return False

def install_packages(modules_path):
    """Install all required packages."""
    logger.info("=" * 60)
    logger.info("INSTALLING PACKAGES")
    logger.info("=" * 60)
    
    # Ensure pip is available (Blender 5.x / some distros may not ship it)
    if not ensure_pip():
        logger.error("Cannot install packages — pip is not available")
        logger.error("Please install pip manually: python -m ensurepip --upgrade")
        logger.error("  Or on Debian/Ubuntu: sudo apt install python3-pip python3.14-venv")
        return False
    
    try:
        # Install all packages in one command
        cmd = [sys.executable, "-m", "pip", "install", "--target", modules_path, "--upgrade"] + REQUIRED_PACKAGES
        
        logger.info("Running: " + " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # If it fails due to PEP 668 externally-managed-environment, retry with flag
        if result.returncode != 0 and "externally-managed-environment" in result.stderr:
            logger.info("Retrying with --break-system-packages (PEP 668)...")
            cmd = [sys.executable, "-m", "pip", "install", "--target", modules_path,
                   "--upgrade", "--break-system-packages"] + REQUIRED_PACKAGES
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("=" * 60)
            logger.info("✓ PACKAGES INSTALLED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info("RESTART BLENDER NOW!")
            logger.info("=" * 60)
            return True
        else:
            logger.error("Installation failed:")
            logger.error(result.stderr)
            return False
    except Exception as e:
        logger.error(f"Installation error: {e}")
        return False

# Initialize modules path
modules_path = get_modules_path()
if modules_path not in sys.path:
    sys.path.append(modules_path)

# Check and install packages
if not are_packages_installed():
    logger.info("First time setup - installing packages...")
    if install_packages(modules_path):
        mark_packages_installed()
        packages_installed = False  # Need restart
    else:
        logger.error("Package installation failed")
        packages_installed = False
else:
    # Try to import packages
    try:
        import google.auth
        import boto3
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        packages_installed = True
        logger.info(f"✓ Packages ready (google-auth {google.auth.__version__})")
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        logger.error("Remove the flag file and restart:")
        logger.error(f"  rm {get_install_flag_path()}")
        packages_installed = False

# Import packages if available
if packages_installed:
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
        import google.auth
    except ImportError as e:
        logger.error(f"Import error: {e}")
        packages_installed = False

#
# HELPER FUNCTIONS
#

def is_gdrive_authenticated():
    """Check if Google Drive is authenticated."""
    token_path = os.path.join(get_credentials_path(), "gdrive_token.pickle")
    if not os.path.exists(token_path):
        return False
    try:
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    return True
                except Exception:
                    # Token refresh failed
                    return False
            return False
        
        return True
    except Exception as e:
        logger.error(f"Auth check error: {e}")
        return False

def get_gdrive_credentials():
    """Get Google Drive credentials."""
    creds = None
    token_path = os.path.join(get_credentials_path(), "gdrive_token.pickle")
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            if os.path.exists(token_path):
                os.remove(token_path)
            return None
    
    return creds

def initialize_s3_client():
    """Initialize S3 client."""
    global s3_client
    if not packages_installed:
        return False
    prefs = bpy.context.preferences.addons[__name__].preferences
    s3_client = boto3.client(
        's3',
        aws_access_key_id=prefs.access_key,
        aws_secret_access_key=prefs.secret_key,
        region_name=prefs.region_name
    )
    return True

def initialize_gdrive_service():
    """Initialize Google Drive service."""
    global drive_service
    if not packages_installed:
        return False
    creds = get_gdrive_credentials()
    if not creds or not creds.valid:
        return False
    drive_service = build('drive', 'v3', credentials=creds)
    return True

def gather_render_outputs():
    """Gather render output files from the current scene's output path."""
    render_files = []
    try:
        output_path = bpy.path.abspath(bpy.context.scene.render.filepath)
        if not output_path:
            logger.info("No render output path set")
            return render_files
        
        # output_path may be a directory or a file prefix
        output_dir = output_path if os.path.isdir(output_path) else os.path.dirname(output_path)
        file_prefix = "" if os.path.isdir(output_path) else os.path.basename(output_path)
        
        if not os.path.isdir(output_dir):
            logger.info(f"Render output directory does not exist: {output_dir}")
            return render_files
        
        # Common render output extensions
        render_extensions = {
            '.png', '.jpg', '.jpeg', '.exr', '.tiff', '.tif', '.bmp',
            '.hdr', '.dpx', '.cin', '.webp',
            '.mp4', '.avi', '.mov', '.mkv',
        }
        
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                if file_prefix and not f.startswith(file_prefix):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in render_extensions:
                    render_files.append(os.path.join(root, f))
        
        logger.info(f"Found {len(render_files)} render output files in {output_dir}")
    except Exception as e:
        logger.error(f"Error gathering render outputs: {e}")
    return render_files


def gather_simulation_cache():
    """Gather simulation/physics cache files from the blend file's cache directory."""
    cache_files = []
    try:
        blend_path = bpy.context.blend_data.filepath
        if not blend_path:
            return cache_files
        
        base_dir = os.path.dirname(blend_path)
        
        # Blender stores caches in blendcache_<filename> by default
        blend_name = os.path.splitext(os.path.basename(blend_path))[0]
        default_cache_dir = os.path.join(base_dir, f"blendcache_{blend_name}")
        
        # Collect from the default bake/cache directory
        cache_dirs_to_scan = set()
        if os.path.isdir(default_cache_dir):
            cache_dirs_to_scan.add(default_cache_dir)
        
        # Also scan for custom cache directories set on point caches
        for obj in bpy.data.objects:
            # Particle systems
            for ps in obj.particle_systems:
                cache = ps.point_cache
                if cache.use_disk_cache:
                    cache_path = bpy.path.abspath(cache.filepath) if cache.filepath else ""
                    if cache_path and os.path.isdir(os.path.dirname(cache_path)):
                        cache_dirs_to_scan.add(os.path.dirname(cache_path))
            
            # Rigid body (world level)
            # Cloth, fluid, soft body modifiers
            for mod in obj.modifiers:
                if hasattr(mod, 'point_cache'):
                    cache = mod.point_cache
                    if cache.use_disk_cache:
                        cache_path = bpy.path.abspath(cache.filepath) if cache.filepath else ""
                        if cache_path and os.path.isdir(os.path.dirname(cache_path)):
                            cache_dirs_to_scan.add(os.path.dirname(cache_path))
                # Fluid simulation (Mantaflow)
                if mod.type == 'FLUID':
                    if mod.fluid_type in ('DOMAIN',) and hasattr(mod, 'domain_settings') and mod.domain_settings:
                        cache_dir = bpy.path.abspath(mod.domain_settings.cache_directory)
                        if cache_dir and os.path.isdir(cache_dir):
                            cache_dirs_to_scan.add(cache_dir)
        
        # Walk cache directories and collect files
        cache_extensions = {
            '.bphys', '.bobj.gz', '.obj.gz', '.gz',
            '.uni', '.vdb', '.openvdb',
            '.abc', '.pc2', '.mdd',
        }
        
        for cache_dir in cache_dirs_to_scan:
            for root, dirs, files in os.walk(cache_dir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    # Handle double extensions like .bobj.gz
                    if f.lower().endswith('.bobj.gz') or f.lower().endswith('.obj.gz') or ext in cache_extensions:
                        cache_files.append(os.path.join(root, f))
        
        logger.info(f"Found {len(cache_files)} simulation cache files")
    except Exception as e:
        logger.error(f"Error gathering simulation cache: {e}")
    return cache_files


def gather_dependencies(blend_file_path, include_renders=False, include_sim_cache=False):
    """Gather all dependencies for a blend file."""
    base_dir = os.path.dirname(blend_file_path)
    package_dir_name = "package_" + os.path.basename(blend_file_path).split('.')[0]
    package_dir = os.path.join(tempfile.gettempdir(), package_dir_name)
    os.makedirs(package_dir, exist_ok=True)
    
    # Copy blend file
    shutil.copy(blend_file_path, package_dir)
    
    # Gather dependencies
    dependencies = set()
    for library in bpy.data.libraries:
        dependencies.add(bpy.path.abspath(library.filepath))
    for image in bpy.data.images:
        if image.filepath:
            dependencies.add(bpy.path.abspath(image.filepath))
    
    # Copy dependencies
    for dep in dependencies:
        if not os.path.exists(dep):
            continue
        rel_path = os.path.relpath(dep, base_dir)
        dep_dest = os.path.join(package_dir, rel_path)
        os.makedirs(os.path.dirname(dep_dest), exist_ok=True)
        shutil.copy(dep, dep_dest)
    
    # Optionally include render outputs
    if include_renders:
        render_files = gather_render_outputs()
        if render_files:
            renders_dest = os.path.join(package_dir, "renders")
            os.makedirs(renders_dest, exist_ok=True)
            for rf in render_files:
                try:
                    dest = os.path.join(renders_dest, os.path.basename(rf))
                    shutil.copy(rf, dest)
                except Exception as e:
                    logger.warning(f"Could not copy render file {rf}: {e}")
            logger.info(f"Included {len(render_files)} render output files")
    
    # Optionally include simulation cache
    if include_sim_cache:
        cache_files = gather_simulation_cache()
        if cache_files:
            cache_dest = os.path.join(package_dir, "sim_cache")
            os.makedirs(cache_dest, exist_ok=True)
            for cf in cache_files:
                try:
                    # Preserve relative directory structure within cache
                    rel = os.path.relpath(cf, base_dir)
                    dest = os.path.join(cache_dest, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy(cf, dest)
                except Exception as e:
                    logger.warning(f"Could not copy cache file {cf}: {e}")
            logger.info(f"Included {len(cache_files)} simulation cache files")
    
    return package_dir

#
# S3 FUNCTIONS
#

def list_files_in_s3(bucket):
    """List files in S3 bucket."""
    if not packages_installed:
        return []
    files = []
    try:
        prefs = bpy.context.preferences.addons[__name__].preferences
        s3_resource = boto3.resource(
            's3',
            aws_access_key_id=prefs.access_key,
            aws_secret_access_key=prefs.secret_key,
            region_name=prefs.region_name
        )
        my_bucket = s3_resource.Bucket(bucket)
        files = [obj.key for obj in my_bucket.objects.all()]
    except Exception as e:
        logger.error(f"S3 list error: {e}")
    return files

def upload_to_s3(folder, bucket, s3_key):
    """Upload folder to S3."""
    if not packages_installed:
        return False
    try:
        for root, dirs, files in os.walk(folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                s3_file_path = os.path.relpath(local_file_path, folder)
                s3_file_path = os.path.join(s3_key, s3_file_path).replace("\\", "/")
                s3_client.upload_file(local_file_path, bucket, s3_file_path)
        return True
    except Exception as e:
        logger.error(f"S3 upload error: {e}")
        return False

def download_from_s3(bucket, s3_key, local_dir):
    """Download project folder from S3, including all dependencies."""
    if not packages_installed:
        return False
    try:
        # Determine the project prefix (folder) from the s3_key
        # Upload stores files as: project_name/file.blend, project_name/textures/img.png, etc.
        if '/' in s3_key:
            prefix = s3_key.rsplit('/', 1)[0] + '/'
        else:
            prefix = s3_key
        
        prefs = bpy.context.preferences.addons[__name__].preferences
        s3_resource = boto3.resource(
            's3',
            aws_access_key_id=prefs.access_key,
            aws_secret_access_key=prefs.secret_key,
            region_name=prefs.region_name
        )
        my_bucket = s3_resource.Bucket(bucket)
        
        blend_file = None
        downloaded_count = 0
        
        for obj in my_bucket.objects.filter(Prefix=prefix):
            # Skip "directory" markers
            if obj.key.endswith('/'):
                continue
            
            local_file_path = os.path.join(local_dir, obj.key)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            s3_client.download_file(bucket, obj.key, local_file_path)
            downloaded_count += 1
            
            if obj.key.endswith('.blend'):
                blend_file = local_file_path
        
        logger.info(f"Downloaded {downloaded_count} files from S3 prefix: {prefix}")
        return blend_file if blend_file else False
    except Exception as e:
        logger.error(f"S3 download error: {e}")
        return False

def delete_from_s3(bucket, s3_file):
    """Delete from S3."""
    if not packages_installed:
        return False
    try:
        s3_client.delete_object(Bucket=bucket, Key=s3_file)
        return True
    except Exception as e:
        logger.error(f"S3 delete error: {e}")
        return False

#
# GOOGLE DRIVE FUNCTIONS
#

def list_files_in_gdrive(folder_id=None):
    """List files in Google Drive."""
    if not packages_installed or not drive_service:
        return []
    files = []
    try:
        # Query for .blend and .zip files
        query = "(name contains '.blend' or name contains '.zip') and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        logger.info(f"Listing files with query: {query}")
        
        # Handle pagination
        files = []
        page_token = None
        
        while True:
            results = drive_service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                orderBy="modifiedTime desc",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            
            if not page_token:
                break
        
        logger.info(f"Found {len(files)} files in Drive")
        
        # Log first 10 files
        for i, f in enumerate(files[:10]):
            logger.info(f"  {i+1}. {f['name']} ({f.get('mimeType', 'unknown')})")
        
    except Exception as e:
        logger.error(f"GDrive list error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    return files

def list_shared_files():
    """List ALL files shared with you (for debugging)."""
    if not packages_installed or not drive_service:
        return []
    
    try:
        logger.info("Listing ALL shared files...")
        
        # List everything shared with you
        results = drive_service.files().list(
            q="sharedWithMe=true and trashed=false",
            fields="files(id, name, mimeType, modifiedTime, owners)",
            orderBy="modifiedTime desc",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        all_files = results.get('files', [])
        logger.info(f"Total shared files: {len(all_files)}")
        
        # Log all files
        for i, f in enumerate(all_files[:50]):  # First 50
            owner = f.get('owners', [{}])[0].get('displayName', 'Unknown')
            logger.info(f"  {i+1}. {f['name']} ({f.get('mimeType')}) by {owner}")
        
        # Filter for .blend and .zip
        blend_files = [f for f in all_files if f['name'].lower().endswith(('.blend', '.zip'))]
        logger.info(f"Found {len(blend_files)} .blend/.zip files")
        
        return blend_files
        
    except Exception as e:
        logger.error(f"Error listing shared files: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def upload_to_gdrive(file_path, folder_id=None):
    """Upload file to Google Drive as zip."""
    if not packages_installed or not drive_service:
        return False
    zip_path = None
    try:
        import zipfile
        
        # If it's a folder, zip it to a temp file (avoids loading entire zip into RAM)
        if os.path.isdir(file_path):
            zip_name = os.path.basename(file_path) + ".zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_name)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        file_path_full = os.path.join(root, file)
                        arcname = os.path.relpath(file_path_full, file_path)
                        zip_file.write(file_path_full, arcname)
            
            file_metadata = {'name': zip_name, 'mimeType': 'application/zip'}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(zip_path, mimetype='application/zip', resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return True
        else:
            # Single file
            file_name = os.path.basename(file_path)
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            media = MediaFileUpload(file_path, resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return True
    except Exception as e:
        logger.error(f"GDrive upload error: {e}")
        return False
    finally:
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)

def extract_dependencies_from_blend(blend_path):
    """Extract actual dependency paths from a .blend file."""
    dependencies = set()
    
    try:
        if not os.path.exists(blend_path):
            logger.error(f"Blend file not found: {blend_path}")
            return dependencies
        
        # Check file size - skip parsing if too large (>500MB)
        file_size = os.path.getsize(blend_path)
        if file_size > 500 * 1024 * 1024:  # 500 MB
            logger.warning(f"Blend file is very large ({file_size / (1024*1024):.1f} MB)")
            logger.warning("Skipping dependency parsing for safety")
            logger.warning("Please upload this file in a dedicated folder with dependencies")
            return dependencies
        
        with open(blend_path, 'rb') as f:
            # Read file header
            header = f.read(12)
            if not header.startswith(b'BLENDER'):
                logger.error("Not a valid .blend file")
                return dependencies
            
            # Find paths with common extensions
            extensions = [
                b'.png', b'.jpg', b'.jpeg', b'.tga', b'.tiff', b'.exr', b'.hdr',
                b'.mp4', b'.mov', b'.avi', b'.blend'
            ]
            
            # Read and scan in chunks to avoid loading entire file into memory
            CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
            MAX_PATH_LEN = 512  # Must exceed the 500-char path length limit below
            
            def _extract_path_at(data, ext_pos, ext):
                """Extract and validate a file path ending at ext_pos."""
                start = ext_pos
                while start > 0 and data[start-1:start] not in [b'\x00', b'\n', b'\r']:
                    start -= 1
                    if ext_pos - start > 500:
                        break
                
                path_bytes = data[start:ext_pos + len(ext)]
                try:
                    path = path_bytes.decode('utf-8', errors='ignore')
                    path = path.strip('\x00\n\r\t ')
                    
                    if len(path) > 3 and ('/' in path or '\\' in path):
                        path = path.replace('\\', '/')
                        if path.startswith('//'):
                            return path[2:]  # Blender relative path
                        elif not path.startswith('/') and ':' not in path:
                            return path
                except (UnicodeDecodeError, ValueError):
                    pass
                return None
            
            prev_tail = b''
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                data = prev_tail + chunk
                is_last_chunk = len(chunk) < CHUNK_SIZE
                
                for ext in extensions:
                    pos = 0
                    while True:
                        pos = data.find(ext, pos)
                        if pos == -1:
                            break
                        
                        # Skip matches in the tail region — next iteration will catch them
                        if not is_last_chunk and pos >= len(data) - MAX_PATH_LEN:
                            pos += 1
                            continue
                        
                        result = _extract_path_at(data, pos, ext)
                        if result:
                            dependencies.add(result)
                        
                        pos += 1
                
                # Keep tail for overlap with next chunk
                if is_last_chunk:
                    break
                prev_tail = chunk[-MAX_PATH_LEN:] if len(chunk) >= MAX_PATH_LEN else chunk
        
        logger.info(f"Extracted {len(dependencies)} dependencies from .blend file:")
        for dep in sorted(dependencies):
            logger.info(f"  - {dep}")
        
        return dependencies
        
    except Exception as e:
        logger.error(f"Error parsing .blend file: {e}")
        return dependencies

def download_from_gdrive(file_id, local_dir):
    """Download and extract from Google Drive."""
    if not packages_installed or not drive_service:
        return False
    try:
        import zipfile
        
        # Get file metadata (including parent folder)
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields='id, name, parents'
        ).execute()
        file_name = file_metadata.get('name')
        
        logger.info(f"Downloading: {file_name}")
        
        # Download file
        temp_file = os.path.join(tempfile.gettempdir(), file_name)
        request = drive_service.files().get_media(fileId=file_id)
        
        with open(temp_file, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        # If zip, extract it
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(local_dir, file_name[:-4])
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            os.remove(temp_file)
            
            # Find .blend file
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.blend'):
                        return os.path.join(root, file)
            
            return None
        
        # If it's a .blend file (not zipped), download dependencies from same folder
        elif file_name.endswith('.blend'):
            logger.info("Non-zipped .blend file detected - analyzing dependencies...")
            
            # Create a directory for this project
            project_name = file_name[:-6]  # Remove .blend
            project_dir = os.path.join(local_dir, project_name)
            os.makedirs(project_dir, exist_ok=True)
            
            # Move the blend file to project directory
            blend_path = os.path.join(project_dir, file_name)
            shutil.move(temp_file, blend_path)
            
            # Parse the .blend file to find actual dependencies
            dependencies = extract_dependencies_from_blend(blend_path)
            
            if not dependencies:
                logger.info("No external dependencies found in .blend file")
                return blend_path
            
            # Get the parent folder of this file
            parents = file_metadata.get('parents', [])
            
            if not parents:
                logger.warning("Could not find parent folder - dependencies cannot be downloaded")
                return blend_path
            
            parent_folder_id = parents[0]
            logger.info(f"Searching for {len(dependencies)} dependencies in parent folder...")
            
            try:
                # Build a map of all files in the parent folder (and subfolders)
                def map_folder_files(folder_id, current_path=""):
                    """Build a map of filename -> file_id for all files in folder tree."""
                    file_map = {}
                    page_token = None
                    
                    query = f"'{folder_id}' in parents and trashed=false"
                    
                    while True:
                        results = drive_service.files().list(
                            q=query,
                            fields="nextPageToken, files(id, name, mimeType)",
                            pageSize=1000,
                            pageToken=page_token,
                            supportsAllDrives=True,
                            includeItemsFromAllDrives=True
                        ).execute()
                        
                        items = results.get('files', [])
                        
                        for item in items:
                            item_name = item['name']
                            item_id = item['id']
                            item_type = item.get('mimeType', '')
                            item_path = f"{current_path}/{item_name}" if current_path else item_name
                            
                            if item_type == 'application/vnd.google-apps.folder':
                                # Recurse into subfolder
                                subfolder_map = map_folder_files(item_id, item_path)
                                file_map.update(subfolder_map)
                            else:
                                # Add file to map (both with and without path for matching)
                                file_map[item_path] = (item_id, item_name)
                                file_map[item_name] = (item_id, item_name)  # Also match just filename
                        
                        page_token = results.get('nextPageToken')
                        if not page_token:
                            break
                    
                    return file_map
                
                # Map all files in parent folder
                logger.info("Mapping files in parent folder...")
                file_map = map_folder_files(parent_folder_id)
                logger.info(f"Found {len(file_map)} files/paths in Drive")
                
                # Download each dependency
                downloaded_count = 0
                for dep_path in dependencies:
                    # Try to find this dependency in the file map
                    found = False
                    
                    # Try exact path match first
                    if dep_path in file_map:
                        file_id, file_name = file_map[dep_path]
                        found = True
                    else:
                        # Try just the filename
                        dep_filename = os.path.basename(dep_path)
                        if dep_filename in file_map:
                            file_id, file_name = file_map[dep_filename]
                            found = True
                    
                    if found:
                        try:
                            # Preserve folder structure from dependency path
                            local_dep_path = os.path.join(project_dir, dep_path)
                            os.makedirs(os.path.dirname(local_dep_path), exist_ok=True)
                            
                            logger.info(f"  Downloading: {dep_path}")
                            file_request = drive_service.files().get_media(fileId=file_id)
                            
                            with open(local_dep_path, 'wb') as dep_fh:
                                dep_downloader = MediaIoBaseDownload(dep_fh, file_request)
                                dep_done = False
                                while not dep_done:
                                    dep_status, dep_done = dep_downloader.next_chunk()
                            
                            downloaded_count += 1
                        except Exception as e:
                            logger.warning(f"  Failed to download {dep_path}: {e}")
                    else:
                        logger.warning(f"  Dependency not found in Drive: {dep_path}")
                
                logger.info(f"Downloaded {downloaded_count}/{len(dependencies)} dependencies")
                
            except Exception as e:
                logger.error(f"Error downloading dependencies: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            return blend_path
        
        else:
            # Other file type, just return it
            return temp_file
            
    except Exception as e:
        logger.error(f"GDrive download error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def delete_from_gdrive(file_id):
    """Delete from Google Drive."""
    if not packages_installed or not drive_service:
        return False
    try:
        drive_service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        logger.error(f"GDrive delete error: {e}")
        return False

def extract_id_from_link(drive_link):
    """Extract file/folder ID from Google Drive link."""
    import re
    
    # Folder: https://drive.google.com/drive/folders/FOLDER_ID
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', drive_link)
    if match:
        return match.group(1), 'folder'
    
    # File: https://drive.google.com/file/d/FILE_ID/view
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', drive_link)
    if match:
        return match.group(1), 'file'
    
    # Open link: https://drive.google.com/open?id=ID
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', drive_link)
    if match:
        return match.group(1), 'unknown'
    
    # Just an ID
    if re.match(r'^[a-zA-Z0-9_-]+$', drive_link):
        return drive_link, 'unknown'
    
    return None, None

def list_files_in_shared_folder(folder_id_or_link):
    """List files in a shared folder."""
    if not packages_installed or not drive_service:
        return []
    
    try:
        file_id, link_type = extract_id_from_link(folder_id_or_link)
        if not file_id:
            logger.error("Invalid Drive link")
            return []
        
        logger.info(f"Browsing: {file_id} (type: {link_type})")
        
        # List files in the folder with pagination
        query = f"'{file_id}' in parents and trashed=false and (name contains '.blend' or name contains '.zip')"
        
        files = []
        page_token = None
        
        while True:
            results = drive_service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            
            if not page_token:
                break
        
        logger.info(f"Found {len(files)} files in folder")
        
        return files
        
    except Exception as e:
        logger.error(f"Error browsing shared folder: {e}")
        return []

#
# BLENDER UI
#

class CloudStoragePreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    # S3 settings
    access_key: bpy.props.StringProperty(name="AWS Access Key", default="", subtype='PASSWORD')
    secret_key: bpy.props.StringProperty(name="AWS Secret Key", default="", subtype='PASSWORD')
    region_name: bpy.props.StringProperty(name="AWS Region", default="us-west-2")
    bucket_name: bpy.props.StringProperty(name="S3 Bucket Name", default="")
    
    # Google Drive settings
    gdrive_client_id: bpy.props.StringProperty(name="Client ID", default="")
    gdrive_client_secret: bpy.props.StringProperty(name="Client Secret", default="", subtype='PASSWORD')
    gdrive_folder_id: bpy.props.StringProperty(name="Folder ID (optional)", default="")
    gdrive_shared_link: bpy.props.StringProperty(
        name="Shared Folder/File Link",
        description="Paste a Google Drive share link to browse or download",
        default=""
    )
    
    storage_provider: bpy.props.EnumProperty(
        name="Storage Provider",
        items=[('S3', "AWS S3", ""), ('GDRIVE', "Google Drive", "")],
        default='GDRIVE'
    )

    def draw(self, context):
        layout = self.layout
        
        if not packages_installed:
            layout.label(text="RESTART BLENDER to complete installation!", icon='ERROR')
            return
        
        layout.prop(self, "storage_provider")
        
        if self.storage_provider == 'S3':
            box = layout.box()
            box.label(text="AWS S3 Settings", icon='SETTINGS')
            box.prop(self, "access_key")
            box.prop(self, "secret_key")
            box.prop(self, "region_name")
            box.prop(self, "bucket_name")
        else:
            box = layout.box()
            box.label(text="Google Drive Settings", icon='SETTINGS')
            box.prop(self, "gdrive_client_id")
            box.prop(self, "gdrive_client_secret")
            box.prop(self, "gdrive_folder_id")
            
            if is_gdrive_authenticated():
                box.label(text="✓ Connected", icon='CHECKMARK')
                box.operator("cloud.gdrive_disconnect", text="Disconnect")
            else:
                if self.gdrive_client_id and self.gdrive_client_secret:
                    box.operator("cloud.gdrive_authenticate", text="Connect to Google Drive", icon='LINKED')

class CloudStoragePanel(bpy.types.Panel):
    bl_label = "Cloud Storage"
    bl_idname = "OBJECT_PT_cloudstorage"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Cloud"
    # Removed bl_options = {'DEFAULT_CLOSED'} so panel stays open
    
    _first_draw = True  # Track if this is the first time drawing

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        
        if not packages_installed:
            layout.label(text="RESTART BLENDER!", icon='ERROR')
            return
        
        prefs = context.preferences.addons[__name__].preferences
        scene = context.scene
        
        layout.prop(prefs, "storage_provider", text="")
        
        if prefs.storage_provider == 'GDRIVE':
            if not is_gdrive_authenticated():
                layout.label(text="Not connected", icon='UNLINKED')
                layout.label(text="Configure in Preferences")
                return
            
            # Shared folder/file section
            box = layout.box()
            box.label(text="Browse Shared Folder/File:", icon='COMMUNITY')
            row = box.row()
            row.prop(prefs, "gdrive_shared_link", text="")
            row.operator("cloud.browse_shared", text="Browse/Refresh", icon='FILE_REFRESH')
        
        # Auto-load files on first draw (if list is empty)
        if len(scene.cloud_file_list) == 0 and CloudStoragePanel._first_draw:
            CloudStoragePanel._first_draw = False
            bpy.ops.cloud.update_list('INVOKE_DEFAULT')
        
        layout.separator()
        
        # File list - simple and clean
        col = layout.column(align=True)
        
        if len(scene.cloud_file_list) == 0:
            col.label(text="No files", icon='INFO')
        else:
            # Show files in boxes for clarity
            for item in scene.cloud_file_list:
                box = col.box()
                box_col = box.column(align=True)
                
                # File name on its own row (full width, no wrapping)
                row = box_col.row()
                row.label(text=item.name, icon='FILE_BLEND')
                
                # Buttons on second row
                row = box_col.row(align=True)
                row.scale_y = 1.2
                row.operator("cloud.load_file", text="Load", icon='IMPORT').file_id = item.file_id
                row.operator("cloud.delete_file", text="Delete", icon='TRASH').file_id = item.file_id
        
        layout.separator()
        
        # Upload options
        box = layout.box()
        box.label(text="Upload Options:", icon='PREFERENCES')
        col = box.column(align=True)
        col.prop(scene, "cloud_include_renders")
        col.prop(scene, "cloud_include_sim_cache")
        
        layout.separator()
        
        # Action buttons
        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("cloud.update_list", text="Refresh", icon='FILE_REFRESH')
        row.operator("cloud.upload", text="Upload", icon='EXPORT')

class CloudFileItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    file_id: bpy.props.StringProperty()

#
# OPERATORS
#

class GoogleDriveAuthenticateOperator(bpy.types.Operator):
    bl_idname = "cloud.gdrive_authenticate"
    bl_label = "Authenticate Google Drive"
    bl_description = "Connect to your Google Drive account via OAuth"

    def execute(self, context):
        if not packages_installed:
            self.report({'ERROR'}, "Restart Blender first")
            return {'CANCELLED'}
        
        prefs = context.preferences.addons[__name__].preferences
        
        try:
            client_config = {
                "installed": {
                    "client_id": prefs.gdrive_client_id,
                    "client_secret": prefs.gdrive_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }
            
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=8080)
            
            token_path = os.path.join(get_credentials_path(), "gdrive_token.pickle")
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            
            global drive_service
            drive_service = build('drive', 'v3', credentials=creds)
            
            self.report({'INFO'}, "Connected to Google Drive!")
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Auth error: {e}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class GoogleDriveDisconnectOperator(bpy.types.Operator):
    bl_idname = "cloud.gdrive_disconnect"
    bl_label = "Disconnect"

    def execute(self, context):
        try:
            token_path = os.path.join(get_credentials_path(), "gdrive_token.pickle")
            if os.path.exists(token_path):
                os.remove(token_path)
            global drive_service
            drive_service = None
            self.report({'INFO'}, "Disconnected")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class BrowseSharedOperator(bpy.types.Operator):
    bl_idname = "cloud.browse_shared"
    bl_label = "Browse Shared"
    bl_description = "Browse files from a shared Google Drive folder or file link"

    def execute(self, context):
        if not packages_installed:
            self.report({'ERROR'}, "Restart Blender")
            return {'CANCELLED'}
        
        if not initialize_gdrive_service():
            self.report({'ERROR'}, "Connect first")
            return {'CANCELLED'}
        
        prefs = context.preferences.addons[__name__].preferences
        shared_link = prefs.gdrive_shared_link.strip()
        
        if not shared_link:
            self.report({'ERROR'}, "Paste a link first")
            return {'CANCELLED'}
        
        try:
            scene = context.scene
            scene.cloud_file_list.clear()
            
            files = list_files_in_shared_folder(shared_link)
            
            if not files:
                self.report({'WARNING'}, "No .blend or .zip files found")
                return {'CANCELLED'}
            
            for file in files:
                new_item = scene.cloud_file_list.add()
                new_item.name = file['name']
                new_item.file_id = file['id']
            
            self.report({'INFO'}, f"Found {len(files)} files")
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Browse error: {e}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class UpdateFileListOperator(bpy.types.Operator):
    bl_idname = "cloud.update_list"
    bl_label = "Update List"
    bl_description = "Refresh the list of files from cloud storage"

    def execute(self, context):
        if not packages_installed:
            self.report({'ERROR'}, "Restart Blender")
            return {'CANCELLED'}
        
        prefs = context.preferences.addons[__name__].preferences
        scene = context.scene
        scene.cloud_file_list.clear()
        
        try:
            if prefs.storage_provider == 'S3':
                initialize_s3_client()
                all_files = list_files_in_s3(prefs.bucket_name)
                blend_files = [f for f in all_files if f.endswith('.blend')]
                
                for file_path in blend_files:
                    new_item = scene.cloud_file_list.add()
                    new_item.name = os.path.basename(file_path)
                    new_item.file_id = file_path
            else:
                if not initialize_gdrive_service():
                    self.report({'ERROR'}, "Connect first")
                    return {'CANCELLED'}
                
                files = list_files_in_gdrive(prefs.gdrive_folder_id or None)
                
                for file in files:
                    new_item = scene.cloud_file_list.add()
                    new_item.name = file['name']
                    new_item.file_id = file['id']
            
            self.report({'INFO'}, f"Found {len(scene.cloud_file_list)} files")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class UploadOperator(bpy.types.Operator):
    bl_idname = "cloud.upload"
    bl_label = "Upload"
    bl_description = "Upload the current .blend file with all dependencies to cloud storage"

    def execute(self, context):
        if not packages_installed:
            self.report({'ERROR'}, "Restart Blender")
            return {'CANCELLED'}
        
        prefs = context.preferences.addons[__name__].preferences
        local_file_path = bpy.context.blend_data.filepath
        
        if not local_file_path:
            self.report({'ERROR'}, "Save file first (Ctrl+S)")
            return {'CANCELLED'}
        
        if not os.path.exists(local_file_path):
            self.report({'ERROR'}, "File does not exist - save first")
            return {'CANCELLED'}
        
        package_dir = None
        try:
            scene = context.scene
            include_renders = scene.cloud_include_renders
            include_sim_cache = scene.cloud_include_sim_cache
            
            if prefs.storage_provider == 'S3':
                if not prefs.bucket_name:
                    self.report({'ERROR'}, "Configure S3 bucket in preferences")
                    return {'CANCELLED'}
                
                initialize_s3_client()
                s3_file_name = os.path.basename(local_file_path).replace(".blend", "")
                package_dir = gather_dependencies(local_file_path, include_renders, include_sim_cache)
                success = upload_to_s3(package_dir, prefs.bucket_name, s3_file_name)
            else:
                if not initialize_gdrive_service():
                    self.report({'ERROR'}, "Connect to Google Drive first")
                    return {'CANCELLED'}
                
                # Gather dependencies and upload as zip
                package_dir = gather_dependencies(local_file_path, include_renders, include_sim_cache)
                success = upload_to_gdrive(package_dir, prefs.gdrive_folder_id or None)
            
            if success:
                # Auto-refresh the file list
                try:
                    bpy.ops.cloud.update_list('EXEC_DEFAULT')
                except:
                    # If auto-refresh fails, just notify user
                    logger.warning("Auto-refresh failed, click Refresh button")
                
                self.report({'INFO'}, "Upload complete!")
            else:
                self.report({'ERROR'}, "Upload failed - check console")
            
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Upload error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.report({'ERROR'}, f"Upload failed: {str(e)[:50]}")
            return {'CANCELLED'}
        finally:
            if package_dir and os.path.exists(package_dir):
                shutil.rmtree(package_dir, ignore_errors=True)

class LoadFileOperator(bpy.types.Operator):
    bl_idname = "cloud.load_file"
    bl_label = "Load File"
    bl_description = "Download and open this file"
    file_id: bpy.props.StringProperty()

    def invoke(self, context, event):
        """Show confirmation dialog before loading."""
        # Check if current file has unsaved changes
        if bpy.data.is_dirty:
            # Show popup menu with clear options
            return context.window_manager.invoke_popup(self, width=400)
        else:
            # No unsaved changes, proceed directly
            return self.execute(context)
    
    def draw(self, context):
        """Draw the popup menu with clear button options."""
        layout = self.layout
        
        # Warning header
        box = layout.box()
        row = box.row()
        row.alert = True
        row.label(text="⚠ UNSAVED CHANGES", icon='ERROR')
        
        layout.separator()
        
        # Explanation
        col = layout.column(align=True)
        col.label(text="Your current project has unsaved changes.")
        col.label(text="Loading a new file will close it.")
        
        layout.separator()
        layout.separator()
        
        # Three clear button options
        col = layout.column(align=True)
        col.scale_y = 1.5
        
        # Option 1: Save and Load (recommended)
        row = col.row()
        row.operator("cloud.save_and_load", text="💾 Save Current & Load New File", icon='FILE_TICK').file_id = self.file_id
        
        # Option 2: Discard and Load
        row = col.row()
        row.operator("cloud.discard_and_load", text="⚠ Discard Changes & Load New File", icon='CANCEL').file_id = self.file_id
        
        # Option 3: Cancel
        row = col.row()
        row.operator("cloud.cancel_load", text="❌ Cancel (Stay in Current File)", icon='BACK')

    def execute(self, context):
        """This should not be called directly when there are unsaved changes."""
        if not packages_installed:
            self.report({'ERROR'}, "Restart Blender")
            return {'CANCELLED'}
        
        # If we get here, there were no unsaved changes, so just load
        prefs = context.preferences.addons[__name__].preferences
        
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), "blender_cloud")
            os.makedirs(temp_dir, exist_ok=True)
            
            if prefs.storage_provider == 'S3':
                initialize_s3_client()
                downloaded_file = download_from_s3(prefs.bucket_name, self.file_id, temp_dir)
            else:
                if not initialize_gdrive_service():
                    self.report({'ERROR'}, "Connect first")
                    return {'CANCELLED'}
                
                downloaded_file = download_from_gdrive(self.file_id, temp_dir)
            
            if downloaded_file and os.path.exists(downloaded_file):
                bpy.ops.wm.open_mainfile(filepath=downloaded_file)
                self.report({'INFO'}, "Loaded!")
            else:
                self.report({'ERROR'}, "Download failed")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class SaveAndLoadFileOperator(bpy.types.Operator):
    bl_idname = "cloud.save_and_load"
    bl_label = "Save Current & Load New File"
    bl_description = "Save your current work, then load the cloud file"
    file_id: bpy.props.StringProperty()

    def execute(self, context):
        # Save current file first
        if bpy.data.filepath:
            try:
                bpy.ops.wm.save_mainfile()
                self.report({'INFO'}, "Current file saved")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to save: {e}")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "Current file has never been saved. Use File → Save As first!")
            return {'CANCELLED'}
        
        # Now load the cloud file
        prefs = context.preferences.addons[__name__].preferences
        
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), "blender_cloud")
            os.makedirs(temp_dir, exist_ok=True)
            
            if prefs.storage_provider == 'S3':
                initialize_s3_client()
                downloaded_file = download_from_s3(prefs.bucket_name, self.file_id, temp_dir)
            else:
                if not initialize_gdrive_service():
                    self.report({'ERROR'}, "Connect first")
                    return {'CANCELLED'}
                
                downloaded_file = download_from_gdrive(self.file_id, temp_dir)
            
            if downloaded_file and os.path.exists(downloaded_file):
                bpy.ops.wm.open_mainfile(filepath=downloaded_file)
                self.report({'INFO'}, "Loaded!")
            else:
                self.report({'ERROR'}, "Download failed")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class DiscardAndLoadFileOperator(bpy.types.Operator):
    bl_idname = "cloud.discard_and_load"
    bl_label = "Discard Changes & Load New File"
    bl_description = "Discard your current changes and load the cloud file"
    file_id: bpy.props.StringProperty()

    def execute(self, context):
        # Just load without saving
        prefs = context.preferences.addons[__name__].preferences
        
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), "blender_cloud")
            os.makedirs(temp_dir, exist_ok=True)
            
            if prefs.storage_provider == 'S3':
                initialize_s3_client()
                downloaded_file = download_from_s3(prefs.bucket_name, self.file_id, temp_dir)
            else:
                if not initialize_gdrive_service():
                    self.report({'ERROR'}, "Connect first")
                    return {'CANCELLED'}
                
                downloaded_file = download_from_gdrive(self.file_id, temp_dir)
            
            if downloaded_file and os.path.exists(downloaded_file):
                bpy.ops.wm.open_mainfile(filepath=downloaded_file)
                self.report({'INFO'}, "Loaded!")
            else:
                self.report({'ERROR'}, "Download failed")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class CancelLoadOperator(bpy.types.Operator):
    bl_idname = "cloud.cancel_load"
    bl_label = "Cancel"
    bl_description = "Cancel loading and stay in current file"

    def execute(self, context):
        self.report({'INFO'}, "Load cancelled")
        return {'FINISHED'}

class DeleteFileOperator(bpy.types.Operator):
    bl_idname = "cloud.delete_file"
    bl_label = "Delete"
    bl_description = "Permanently delete this file from cloud storage"
    file_id: bpy.props.StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if not packages_installed:
            self.report({'ERROR'}, "Restart Blender")
            return {'CANCELLED'}
        
        prefs = context.preferences.addons[__name__].preferences
        
        try:
            if prefs.storage_provider == 'S3':
                initialize_s3_client()
                success = delete_from_s3(prefs.bucket_name, self.file_id)
            else:
                if not initialize_gdrive_service():
                    self.report({'ERROR'}, "Connect first")
                    return {'CANCELLED'}
                
                success = delete_from_gdrive(self.file_id)
            
            if success:
                # Auto-refresh the file list
                try:
                    bpy.ops.cloud.update_list('EXEC_DEFAULT')
                except:
                    logger.warning("Auto-refresh failed, click Refresh button")
                
                self.report({'INFO'}, "Deleted!")
            else:
                self.report({'ERROR'}, "Delete failed")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

#
# REGISTRATION
#

# Handler to refresh file list after loading a file
@bpy.app.handlers.persistent
def refresh_after_load(dummy):
    """Auto-refresh cloud file list after loading a file."""
    def do_refresh():
        try:
            # Check if we're authenticated and refresh
            prefs = bpy.context.preferences.addons.get(__name__)
            if prefs and prefs.preferences:
                if prefs.preferences.storage_provider == 'GDRIVE':
                    if is_gdrive_authenticated():
                        bpy.ops.cloud.update_list('EXEC_DEFAULT')
                elif prefs.preferences.storage_provider == 'S3':
                    bpy.ops.cloud.update_list('EXEC_DEFAULT')
        except Exception as e:
            # If refresh fails, no big deal
            logger.debug(f"Auto-refresh after load failed: {e}")
        return None  # Don't repeat timer
    
    # Use a timer to refresh after a short delay (let Blender settle)
    bpy.app.timers.register(do_refresh, first_interval=1.0)

def register():
    bpy.utils.register_class(CloudStoragePreferences)
    bpy.utils.register_class(CloudStoragePanel)
    bpy.utils.register_class(CloudFileItem)
    bpy.utils.register_class(GoogleDriveAuthenticateOperator)
    bpy.utils.register_class(GoogleDriveDisconnectOperator)
    bpy.utils.register_class(BrowseSharedOperator)
    bpy.utils.register_class(UpdateFileListOperator)
    bpy.utils.register_class(UploadOperator)
    bpy.utils.register_class(LoadFileOperator)
    bpy.utils.register_class(SaveAndLoadFileOperator)
    bpy.utils.register_class(DiscardAndLoadFileOperator)
    bpy.utils.register_class(CancelLoadOperator)
    bpy.utils.register_class(DeleteFileOperator)
    bpy.types.Scene.cloud_file_list = bpy.props.CollectionProperty(type=CloudFileItem)
    bpy.types.Scene.cloud_include_renders = bpy.props.BoolProperty(
        name="Include Render Outputs",
        description="Include rendered images/videos from the output path in the upload",
        default=False
    )
    bpy.types.Scene.cloud_include_sim_cache = bpy.props.BoolProperty(
        name="Include Simulation Cache",
        description="Include physics and fluid simulation cache files in the upload",
        default=False
    )
    
    # Register load handler to auto-refresh after loading files
    if refresh_after_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(refresh_after_load)

def unregister():
    bpy.utils.unregister_class(CloudStoragePreferences)
    bpy.utils.unregister_class(CloudStoragePanel)
    bpy.utils.unregister_class(CloudFileItem)
    bpy.utils.unregister_class(GoogleDriveAuthenticateOperator)
    bpy.utils.unregister_class(GoogleDriveDisconnectOperator)
    bpy.utils.unregister_class(BrowseSharedOperator)
    bpy.utils.unregister_class(UpdateFileListOperator)
    bpy.utils.unregister_class(UploadOperator)
    bpy.utils.unregister_class(LoadFileOperator)
    bpy.utils.unregister_class(SaveAndLoadFileOperator)
    bpy.utils.unregister_class(DiscardAndLoadFileOperator)
    bpy.utils.unregister_class(CancelLoadOperator)
    bpy.utils.unregister_class(DeleteFileOperator)
    del bpy.types.Scene.cloud_file_list
    del bpy.types.Scene.cloud_include_renders
    del bpy.types.Scene.cloud_include_sim_cache
    
    # Unregister load handler
    if refresh_after_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(refresh_after_load)

if __name__ == "__main__":
    register()