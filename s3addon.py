bl_info = {
    "name": "Blender S3 Integration",
    "author": "Kashish aka MrKuros",
    "version": (2, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Tool Shelf > S3 Integration",
    "description": "Upload and download Blender files to/from AWS S3",
    "category": "Development",
}

import bpy
import os
import sys
import shutil
import tempfile
import logging
import subprocess
import threading

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

REQUIRED_PACKAGES = ["boto3"]

# Global variables
s3_client = None
packages_installed = False

def get_modules_path():
    """Get the Blender user modules path."""
    return bpy.utils.user_resource("SCRIPTS", path="modules", create=True)

def append_modules_to_sys_path(modules_path):
    """Add modules path to sys.path if not already present."""
    if modules_path not in sys.path:
        sys.path.append(modules_path)

def check_packages_installed():
    """Check if all required packages are installed."""
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            return False
    return True

def install_packages_sync(packages, modules_path):
    """Install required packages synchronously."""
    for package in packages:
        try:
            __import__(package)
            logger.info(f"'{package}' is already installed.")
        except ImportError:
            logger.info(f"Installing '{package}'...")
            try:
                subprocess.check_call([
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "--target",
                    modules_path,
                    package
                ])
                logger.info(f"'{package}' installed successfully.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install '{package}'. Error: {e}")
                return False
    return True

# Initialize modules path and install packages
modules_path = get_modules_path()
append_modules_to_sys_path(modules_path)

# Try to install packages if not already installed
if not check_packages_installed():
    logger.info("Installing required packages...")
    packages_installed = install_packages_sync(REQUIRED_PACKAGES, modules_path)
else:
    packages_installed = True
    logger.info("All required packages are already installed.")

# Import boto3 after ensuring it's installed
if packages_installed:
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError
    except ImportError:
        logger.error("Failed to import boto3. Please restart Blender.")
        packages_installed = False

class S3IntegrationPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    access_key: bpy.props.StringProperty(
        name="Access Key",
        description="AWS Access Key",
        default="",
        subtype='PASSWORD'
    )
    secret_key: bpy.props.StringProperty(
        name="Secret Key",
        description="AWS Secret Key",
        default="",
        subtype='PASSWORD'
    )
    region_name: bpy.props.StringProperty(
        name="Region Name",
        description="AWS Region Name",
        default="us-west-2"
    )
    bucket_name: bpy.props.StringProperty(
        name="Bucket Name",
        description="S3 Bucket Name",
        default=""
    )

    def draw(self, context):
        """Draw the preferences UI."""
        layout = self.layout
        
        if not packages_installed:
            layout.label(text="Required packages not installed!", icon='ERROR')
            layout.label(text="Please restart Blender to complete installation.")
            return
        
        layout.prop(self, "access_key")
        layout.prop(self, "secret_key")
        layout.prop(self, "region_name")
        layout.prop(self, "bucket_name")

def initialize_s3_client():
    """Initialize the S3 client."""
    global s3_client
    if not packages_installed:
        logger.error("Cannot initialize S3 client: boto3 not installed")
        return False
    
    prefs = bpy.context.preferences.addons[__name__].preferences
    s3_client = boto3.client(
        's3',
        aws_access_key_id=prefs.access_key,
        aws_secret_access_key=prefs.secret_key,
        region_name=prefs.region_name
    )
    return True

def list_files_in_bucket(bucket):
    """List all files in an S3 bucket."""
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
        logger.error(f"Error listing files: {e}")
    return files

def gather_dependencies(blend_file_path):
    """Gather all dependencies of the blend file and copy them to a new folder."""
    base_dir = os.path.dirname(blend_file_path)
    package_dir_name = "package_" + os.path.basename(blend_file_path).split('.')[0]
    package_dir = os.path.join(tempfile.gettempdir(), package_dir_name)

    # Create a new directory to store the blend file and dependencies
    os.makedirs(package_dir, exist_ok=True)

    # Copy the blend file while preserving the relative path
    shutil.copy(blend_file_path, package_dir)

    # List to store paths of dependencies
    dependencies = set()

    # Add all linked libraries
    for library in bpy.data.libraries:
        dependencies.add(bpy.path.abspath(library.filepath))

    # Add all image filepaths (textures)
    for image in bpy.data.images:
        if image.filepath:
            dependencies.add(bpy.path.abspath(image.filepath))

    # Copy all dependencies to the new directory, preserving the relative paths
    for dep in dependencies:
        rel_path = os.path.relpath(dep, base_dir)
        dep_dest = os.path.join(package_dir, rel_path)
        os.makedirs(os.path.dirname(dep_dest), exist_ok=True)
        shutil.copy(dep, dep_dest)

    return package_dir

def upload_folder_to_s3(folder, bucket, s3_key):
    """Upload a folder to AWS S3 without zipping."""
    if not packages_installed:
        logger.error("Cannot upload: boto3 not installed")
        return False
    
    try:
        for root, dirs, files in os.walk(folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                s3_file_path = os.path.relpath(local_file_path, folder)
                s3_file_path = os.path.join(s3_key, s3_file_path)
                s3_client.upload_file(local_file_path, bucket, s3_file_path)
                logger.info(f"Uploaded {local_file_path} to {s3_file_path} in {bucket}")
        logger.info(f"Uploaded {folder} to {s3_key} in {bucket}")
        return True
    except NoCredentialsError:
        logger.error("Credentials not available")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

def download_from_s3(bucket, s3_key, local_dir):
    """Download a file from AWS S3 to a local directory, ensuring correct path structure."""
    if not packages_installed:
        logger.error("Cannot download: boto3 not installed")
        return False
    
    try:
        # Get the filename from the S3 key and ensure proper path
        file_name = os.path.basename(s3_key)
        local_file_path = os.path.join(local_dir, file_name)

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        # Download the file
        logger.info(f"Downloading {s3_key} from bucket {bucket} to {local_file_path}")
        s3_client.download_file(bucket, s3_key, local_file_path)
        logger.info(f"Downloaded {s3_key} to {local_file_path}")
        
        return local_file_path
    except NoCredentialsError:
        logger.error("Credentials not available")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

def load_s3_file_into_blender(file_name):
    """Download and load an S3 file into Blender."""
    if not packages_installed:
        logger.error("Cannot load file: boto3 not installed")
        return
    
    try:
        temp_dir = os.path.join(tempfile.gettempdir(), "blender_s3_package", "skinmodel")
        os.makedirs(temp_dir, exist_ok=True)

        # Ensure S3 client is initialized
        initialize_s3_client()

        # Download the file
        downloaded_file = download_from_s3(
            bpy.context.preferences.addons[__name__].preferences.bucket_name,
            file_name,
            temp_dir
        )
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            raise FileNotFoundError(f"Failed to download {file_name} from S3.")
        
        # Load the downloaded file into Blender
        bpy.ops.wm.open_mainfile(filepath=downloaded_file)
        logger.info("File Loaded Successfully")
    except NoCredentialsError:
        logger.error("Credentials not available")
    except FileNotFoundError as e:
        logger.error(str(e))
    except Exception as e:
        logger.error(f"An error occurred: {e}")

def delete_file_from_s3(bucket, s3_file):
    """Delete a file from AWS S3."""
    if not packages_installed:
        logger.error("Cannot delete: boto3 not installed")
        return False
    
    try:
        s3_client.delete_object(Bucket=bucket, Key=s3_file)
        logger.info(f"Deleted {s3_file} from {bucket}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete {s3_file}: {e}")
        return False

class S3IntegrationPanel(bpy.types.Panel):
    bl_label = "S3 Integration"
    bl_idname = "OBJECT_PT_s3integration"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "S3 Integration"

    def draw(self, context):
        """Draw the panel UI."""
        layout = self.layout
        
        if not packages_installed:
            layout.label(text="Required packages not installed!", icon='ERROR')
            layout.label(text="Please restart Blender.")
            return
        
        scene = context.scene
        col = layout.column()

        # List all files in the scene's custom list
        for item in scene.my_list:
            row = col.row()
            row.label(text=item.name)
            row.operator("s3integration.load_file", text="Load").file_name = item.name
            row.operator("s3integration.delete_file", text="Delete").file_name = item.name

        layout.operator("scene.update_list", text="Update List")
        layout.operator("s3integration.upload", text="Upload to S3")

class MyPropGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

class UpdateFileListOperator(bpy.types.Operator):
    bl_idname = "scene.update_list"
    bl_label = "Update List"

    def execute(self, context):
        """Update the scene's list of files from S3, showing only .blend files."""
        if not packages_installed:
            self.report({'ERROR'}, "Required packages not installed. Please restart Blender.")
            return {'CANCELLED'}
        
        initialize_s3_client()  # Ensure S3 client is initialized
        scene = context.scene

        # Get all files from the S3 bucket
        all_files = list_files_in_bucket(bpy.context.preferences.addons[__name__].preferences.bucket_name)
        
        # Filter to include only .blend files
        blend_files = [file_name for file_name in all_files if file_name.endswith('.blend')]

        # Clear the current list and populate it with filtered blend files
        scene.my_list.clear()
        for blend_file in blend_files:
            blend_file = blend_file.split('/')[-1]  # Get only the filename
            new_item = scene.my_list.add()
            new_item.name = blend_file

        return {'FINISHED'}

class UploadOperator(bpy.types.Operator):
    bl_idname = "s3integration.upload"
    bl_label = "Upload to S3"

    def execute(self, context):
        """Upload the current Blender file to S3."""
        if not packages_installed:
            self.report({'ERROR'}, "Required packages not installed. Please restart Blender.")
            return {'CANCELLED'}
        
        initialize_s3_client()  # Ensure S3 client is initialized
        local_file_path = bpy.context.blend_data.filepath
        
        if not local_file_path:
            self.report({'ERROR'}, "Please save your file before uploading.")
            return {'CANCELLED'}
        
        s3_file_name = os.path.basename(local_file_path).replace(".blend", "")

        # Gather dependencies and create a package directory
        package_dir = gather_dependencies(local_file_path)

        # Upload the package directory to S3 without zipping
        success = upload_folder_to_s3(package_dir, bpy.context.preferences.addons[__name__].preferences.bucket_name, s3_file_name)

        # Clean up: remove the temporary package directory after upload
        shutil.rmtree(package_dir)

        if success:
            # Update the list of files in the panel after upload
            bpy.ops.scene.update_list()
            self.report({'INFO'}, "File uploaded successfully!")
        else:
            self.report({'ERROR'}, "Failed to upload file.")

        return {'FINISHED'}

class LoadFileOperator(bpy.types.Operator):
    bl_idname = "s3integration.load_file"
    bl_label = "Load File from S3"

    file_name: bpy.props.StringProperty()

    def execute(self, context):
        """Download and load the selected file from S3."""
        if not packages_installed:
            self.report({'ERROR'}, "Required packages not installed. Please restart Blender.")
            return {'CANCELLED'}
        
        load_s3_file_into_blender(self.file_name)
        return {'FINISHED'}

class DeleteFileOperator(bpy.types.Operator):
    bl_idname = "s3integration.delete_file"
    bl_label = "Delete File from S3"

    file_name: bpy.props.StringProperty()

    def execute(self, context):
        """Delete the selected file from S3."""
        if not packages_installed:
            self.report({'ERROR'}, "Required packages not installed. Please restart Blender.")
            return {'CANCELLED'}
        
        initialize_s3_client()  # Ensure S3 client is initialized
        success = delete_file_from_s3(bpy.context.preferences.addons[__name__].preferences.bucket_name, self.file_name)

        if success:
            # Update the list of files in the panel after deletion
            bpy.ops.scene.update_list()
            self.report({'INFO'}, "File deleted successfully!")
        else:
            self.report({'ERROR'}, "Failed to delete file.")

        return {'FINISHED'}

def register():
    bpy.utils.register_class(S3IntegrationPreferences)
    bpy.utils.register_class(S3IntegrationPanel)
    bpy.utils.register_class(UpdateFileListOperator)
    bpy.utils.register_class(UploadOperator)
    bpy.utils.register_class(LoadFileOperator)
    bpy.utils.register_class(DeleteFileOperator)
    bpy.utils.register_class(MyPropGroup)
    bpy.types.Scene.my_list = bpy.props.CollectionProperty(type=MyPropGroup)

def unregister():
    bpy.utils.unregister_class(S3IntegrationPreferences)
    bpy.utils.unregister_class(S3IntegrationPanel)
    bpy.utils.unregister_class(UpdateFileListOperator)
    bpy.utils.unregister_class(UploadOperator)
    bpy.utils.unregister_class(LoadFileOperator)
    bpy.utils.unregister_class(DeleteFileOperator)
    bpy.utils.unregister_class(MyPropGroup)
    del bpy.types.Scene.my_list

if __name__ == "__main__":
    register()
