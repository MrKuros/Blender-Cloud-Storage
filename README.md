# Blender Cloud Storage v3.0

Upload and download Blender files with all dependencies to **AWS S3** and **Google Drive**.

**Author:** Kashish aka MrKuros  
**GitHub:** https://github.com/mrkuros  
**License:** MIT  
**Blender Version:** 3.0+ (tested on 3.x, 4.x, 5.x)

---

## 📑 Table of Contents

1. [Quick Start](#-quick-start)
2. [Platform Support](#️-platform-support)
3. [Features](#-features)
4. [Installation](#-installation)
   - 4.1 [Download](#step-1-download)
   - 4.2 [Install in Blender](#step-2-install-in-blender)
   - 4.3 [Package Installation](#step-3-first-time---package-installation)
   - 4.4 [Verify Installation](#step-4-verify-installation)
5. [Configuration](#-configuration)
   - 5.1 [Google Drive Setup](#option-a-google-drive-recommended-for-collaboration)
   - 5.2 [AWS S3 Setup](#option-b-aws-s3)
   - 5.3 [Security Notes](#security-notes)
6. [Usage](#-usage)
   - 6.1 [Upload](#upload-a-file)
   - 6.2 [Download](#download-a-file)
   - 6.3 [Browse Shared Folders](#browse-shared-folders-google-drive-only)
   - 6.4 [Delete](#delete-a-file)
7. [Google Drive Folder ID](#️-google-drive-folder-id-optional)
8. [Troubleshooting](#-troubleshooting)
9. [Privacy & Permissions](#-privacy--permissions)
10. [Use Cases](#-use-cases)
11. [Best Practices](#-best-practices)
12. [Known Issues](#-known-issues)
13. [Technical Details](#-technical-details)
14. [Updating the Addon](#-updating-the-addon)
15. [Contributing](#-contributing)
16. [License](#-license)
17. [Quick Start Checklist](#-quick-start-checklist)

**💡 Tip:** The links work on GitHub. If viewing locally, use section numbers (e.g., "Section 5.1" for Google Drive setup) or scroll to find sections.

---

## 1. 🖥️ Platform Support

- ✅ **Windows** 10/11 (fully tested)
- ✅ **macOS** 10.15+ (Intel & Apple Silicon)
- ✅ **Linux** (Ubuntu, Fedora, Arch, etc.)

**All platforms use:**
- Cross-platform file paths (automatic)
- System temp directories (automatic)
- Platform-appropriate Blender config paths

---

## 1. 🚀 Quick Start

1. **Download** `blender_cloud_storage_v3.py` from [releases](https://github.com/mrkuros/bloc/releases)
2. **Install** in Blender (Edit → Preferences → Add-ons → Install)
3. **Wait** 30-60 seconds for package installation (first time only)
4. **Restart** Blender
5. **Configure** Google Drive or AWS S3 credentials
6. **Done!** Find the panel in 3D Viewport sidebar (press N → Cloud tab)

---

## ⚠️ IMPORTANT - First Time Setup Warning

**When you first install this addon, Blender will:**
1. **Freeze for 30-60 seconds** while installing Python packages
2. Show "Installing packages..." in the console
3. Require you to **RESTART BLENDER** to complete installation

**This is normal!** The addon needs to install Google Drive and AWS packages. This only happens ONCE.

After the first restart, Blender will start normally and the addon will work instantly.

---

## 3. 📋 Features

- ✅ **Upload** .blend files with ALL dependencies (textures, linked files, etc.)
- ✅ **Download** files with dependencies intact
- ✅ **AWS S3 support** - Upload to your S3 bucket
- ✅ **Google Drive support** - Upload to your Google Drive
- ✅ **Browse shared folders** - Access files others have shared with you
- ✅ **Cross-platform** - Works on Windows, macOS, Linux
- ✅ **All Blender versions** - Supports Blender 3.0 through 5.x and beyond

---

## 4. 📥 Installation

### Step 1: Download

Download `blender_cloud_storage_v3.py` from the releases page.

### Step 2: Install in Blender

1. Open Blender
2. Go to **Edit → Preferences → Add-ons**
3. Click **"Install..."** (top right)
4. Select `blender_cloud_storage_v3.py`
5. Click **"Install Add-on"**
6. **Enable the checkbox** next to "Development: Blender Cloud Storage"

### Step 3: First Time - Package Installation

**⚠️ CRITICAL: Read this carefully!**

When you enable the addon for the first time:

1. **Blender will freeze** - This is NORMAL! Don't panic!
2. **Check the console** (Window → Toggle System Console)
3. You'll see:
   ```
   Installing packages...
   Running: python -m pip install ...
   ```
4. **Wait 30-60 seconds** for installation to complete
5. Console will show:
   ```
   ✓ PACKAGES INSTALLED SUCCESSFULLY
   RESTART BLENDER NOW!
   ```
6. **Close and restart Blender**

### Step 4: Verify Installation

After restart:
1. Press **N** in the 3D Viewport
2. Look for **"Cloud"** tab in the sidebar
3. If you see it → ✅ Installation successful!

**Note:** Package installation only happens ONCE. After this, Blender starts normally.

---

## 5. 🔧 Configuration

### Option A: Google Drive (Recommended for Collaboration)

#### Part 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create a new project (e.g., "Blender Cloud Storage")
3. Enable **Google Drive API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

#### Part 2: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. If prompted, configure OAuth consent screen:
   - User Type: **External**
   - App name: "Blender Cloud Storage"
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Skip (default is fine)
   - Test users: Add your email
   - Click **"Save and Continue"** until done
4. Back to "Create Credentials":
   - Application type: **Desktop app**
   - Name: "Blender Cloud Storage"
   - Click **"Create"**
5. **Copy the Client ID and Client Secret** - you'll need these!

#### Part 3: Configure in Blender

1. In Blender: **Edit → Preferences → Add-ons**
2. Find **"Blender Cloud Storage"** and expand it
3. Select **"Google Drive"** from dropdown
4. Paste your **Client ID**
5. Paste your **Client Secret**
6. *(Optional)* Enter a **Folder ID** if you want to use a specific folder
7. Click **"Connect to Google Drive"**
8. Browser will open asking for permissions:
   ```
   Blender Cloud Storage wants to:
   See, edit, create, and delete all of your Google Drive files
   ```
9. Click **"Allow"**
10. Return to Blender - you should see **"✓ Connected"**

**Note:** The addon needs full Drive access to see your existing files and shared folders.

---

### Option B: AWS S3

#### Part 1: Create AWS Account & IAM User

1. **Create AWS Account** at https://aws.amazon.com (if you don't have one)
2. **Go to IAM Console**: https://console.aws.amazon.com/iam/
3. **Create a new user**:
   - Click **"Users"** in the left sidebar
   - Click **"Create user"**
   - **User name:** `blender-cloud-storage`
   - Click **"Next"**

#### Part 2: Set Permissions

1. **Select permissions**:
   - Choose **"Attach policies directly"**
   - Search for: `AmazonS3FullAccess`
   - Check the box next to it
   - Click **"Next"**
2. **Review and create**:
   - Click **"Create user"**

#### Part 3: Create Access Keys

1. **Select your new user** from the users list
2. Go to **"Security credentials"** tab
3. Scroll down to **"Access keys"**
4. Click **"Create access key"**
5. **Select use case**: Choose **"Application running outside AWS"**
6. Click **"Next"**
7. *(Optional)* Add description: "Blender Cloud Storage"
8. Click **"Create access key"**
9. **⚠️ IMPORTANT:** Copy both:
   - **Access key ID** (looks like: `AKIAIOSFODNN7EXAMPLE`)
   - **Secret access key** (looks like: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)
   
   **Save these somewhere safe! You can't see the secret again!**

10. Click **"Done"**

#### Part 4: Create S3 Bucket

1. **Go to S3 Console**: https://s3.console.aws.amazon.com/
2. Click **"Create bucket"**
3. **Bucket settings**:
   - **Bucket name:** Choose a unique name (e.g., `my-blender-projects-2024`)
   - **AWS Region:** Choose closest to you (e.g., `us-west-2`, `eu-west-1`)
   - **Block all public access:** Keep this CHECKED (recommended for security)
4. Click **"Create bucket"**

#### Part 5: Configure in Blender

1. In Blender: **Edit → Preferences → Add-ons**
2. Find **"Blender Cloud Storage"** and expand it
3. Select **"AWS S3"** from dropdown
4. Enter your credentials:
   - **AWS Access Key:** Paste your access key ID
   - **AWS Secret Key:** Paste your secret access key
   - **AWS Region:** Enter the region you chose (e.g., `us-west-2`)
   - **S3 Bucket Name:** Enter your bucket name
5. Done! Start uploading files

---

### Security Notes

**AWS Credentials:**
- ✅ Never share your access keys
- ✅ Store them securely (password manager recommended)
- ✅ If compromised, delete them in IAM console and create new ones
- ✅ Consider using AWS IAM roles for production use

**AWS Costs:**
- 💰 S3 Storage: ~$0.023 per GB/month (first 50 TB)
- 💰 Data Transfer OUT: First 100 GB/month free, then ~$0.09 per GB
- 💰 Data Transfer IN: Free
- 💰 Example: 100 GB stored + 10 GB downloads/month ≈ $2.30/month
- 📊 Check pricing: https://aws.amazon.com/s3/pricing/

**Google Drive:**
- ✅ OAuth tokens stored locally in Blender
- ✅ Can revoke access anytime from Google Account settings
- ✅ Only requests access to Drive files, nothing else
- 💰 Free: 15 GB included with Google account
- 💰 Paid: Google One plans start at $1.99/month for 100 GB

---

## 6. 📖 Usage

### Upload a File

1. **Save your .blend file** (Ctrl+S)
2. Press **N** in 3D Viewport → **Cloud** tab
3. Click **"Upload"**
4. Wait for upload to complete
5. Done! Your file + all dependencies are uploaded

**What gets uploaded:**
- Your .blend file
- All textures
- All linked libraries
- All referenced images
- Everything packaged as a .zip file

---

### Download a File

1. Press **N** in 3D Viewport → **Cloud** tab
2. Click **"Refresh"** to see your files
3. Find your file in the list
4. Click **"Load"** next to the file name
5. **⚠️ If you have unsaved changes**, a popup menu appears with 3 clear options:

```
┌─────────────────────────────────────────┐
│         ⚠ UNSAVED CHANGES                │
├─────────────────────────────────────────┤
│                                          │
│ Your current project has unsaved changes.│
│ Loading a new file will close it.       │
│                                          │
│  [💾 Save Current & Load New File]      │
│                                          │
│  [⚠ Discard Changes & Load New File]    │
│                                          │
│  [❌ Cancel (Stay in Current File)]      │
│                                          │
└─────────────────────────────────────────┘
```

**Choose one:**
- **💾 Save Current & Load New File** - Saves your work, then loads the cloud file (recommended!)
- **⚠ Discard Changes & Load New File** - Discards your changes and loads the cloud file
- **❌ Cancel** - Closes popup, stays in your current file

6. File downloads and opens automatically with all dependencies!

**Note:** If you haven't saved your file yet (untitled), the "Save" option will warn you to save manually first.

**Smart Dependency Detection:**

- **Zipped files (.zip):** Extracts everything and opens the .blend file
- **Non-zipped .blend files:** **Intelligently parses the .blend file** to find actual dependencies:
  1. Analyzes the .blend file to extract all referenced paths
  2. Finds textures, HDRIs, videos, linked files actually used
  3. Downloads ONLY those specific files from the Drive folder
  4. Preserves folder structure (e.g., `hdri/`, `textures/`)
  5. **No arbitrary limits** - downloads exactly what's needed!

This means the plugin reads your .blend file to see what it actually needs, then downloads only those files. No more downloading entire folders or hitting file limits!

**Example:** If your .blend file references:
```
//hdri/studio.exr
//textures/diffuse.png
//textures/normal.png
```

The plugin will:
1. Parse the .blend file
2. Find these 3 dependencies
3. Download ONLY these 3 files from Drive
4. Recreate the folder structure locally

**Works anywhere:** Files can be in your root Drive, shared folders, anywhere - as long as the dependencies are in the same parent folder, they'll be found and downloaded!

**Note:** For best results, always use the "Upload" button which packages everything properly. But loose files work great too!

**Note:** For best results, always upload as a package (using the Upload button) which zips everything properly. But the addon handles loose files too!

---

### Browse Shared Folders (Google Drive Only)

**Scenario:** Someone shared a Google Drive folder with you containing Blender files.

1. Get the share link from them:
   ```
   https://drive.google.com/drive/folders/ABC123XYZ...
   ```
2. In Blender Cloud panel:
   - Paste the link in **"Browse Shared Folder/File"** field
   - Click **"Browse/Refresh"**
3. Files from that folder will appear in the list
4. Click **"Load"** to open any file

**To check for updates:**
- Click **"Browse/Refresh"** again with the same link
- The list will update with any new files added to the shared folder

**Important:** The folder must be shared with the Google account you connected in Blender.

---

### Delete a File

1. Find the file in the list
2. Click **"Del"** next to the file name
3. Confirm deletion

---

## 7. 🗂️ Google Drive Folder ID (Optional)

If you want to organize your files in a specific Google Drive folder:

1. Create a folder in Google Drive (e.g., "Blender Projects")
2. Open the folder
3. Copy the Folder ID from the URL:
   ```
   https://drive.google.com/drive/folders/1a2B3c4D5e6F7g8H9
                                           ^^^^^^^^^^^^^^^^^^^
                                           This is the Folder ID
   ```
4. In Blender Preferences → Cloud Storage addon
5. Paste the Folder ID in **"Folder ID (optional)"**
6. Click **"Disconnect"** then **"Connect to Google Drive"** again

Now all uploads/downloads will use that folder instead of your Drive root.

---

## 8. ⚠️ Troubleshooting

### "Blender froze on first install!"

**This is normal!** Blender is installing Python packages. Check the console (Window → Toggle System Console) to see progress. Wait 30-60 seconds, then restart Blender.

---

### "Packages keep reinstalling every time!"

This should NOT happen. If it does:

1. Check console for errors
2. Manually verify flag file exists:

**Windows:**
```powershell
dir "%APPDATA%\Blender Foundation\Blender\[VERSION]\scripts\addons\cloud_storage_data\.packages_v3"
```

**macOS:**
```bash
ls ~/Library/Application\ Support/Blender/[VERSION]/scripts/addons/cloud_storage_data/.packages_v3
```

**Linux:**
```bash
ls ~/.config/blender/[VERSION]/scripts/addons/cloud_storage_data/.packages_v3
```

3. If missing, packages will reinstall (which is correct)
4. If file exists but still reinstalling, remove it and let it reinstall fresh:

**Windows:**
```powershell
del "%APPDATA%\Blender Foundation\Blender\[VERSION]\scripts\addons\cloud_storage_data\.packages_v3"
```

**macOS/Linux:**
```bash
# macOS:
rm ~/Library/Application\ Support/Blender/[VERSION]/scripts/addons/cloud_storage_data/.packages_v3
# Linux:
rm ~/.config/blender/[VERSION]/scripts/addons/cloud_storage_data/.packages_v3
```

---

### "No files found" (Google Drive)

**Check these:**

1. **Did you click "Refresh"?** The plugin doesn't auto-refresh
2. **Are you connected?** Look for "✓ Connected" in preferences
3. **Do you have .blend or .zip files in Drive?** The plugin only shows these
4. **Check the console** - it shows what files were found:
   ```
   Found 5 files in Drive
   1. project1.blend
   2. animation.zip
   ...
   ```

---

### "Can't see shared files"

**For shared folders to work:**

1. Folder must be shared with YOUR Google account email
2. You must be connected with that SAME account in Blender
3. Try pasting the folder link in "Browse Shared Folder/File" and clicking "Browse"

**To check:** Open the folder link in your browser. Can you see it? If not, it's not shared with you.

---

### "OAuth error" or "Access denied"

**If you see this during Google Drive connection:**

1. Go to Google Cloud Console
2. OAuth consent screen
3. Add your email to **"Test users"**
4. OR publish the app (will show "unverified" warning but works)

---

### "Import failed: No module named 'google'"

**The packages didn't install properly.**

1. Check if you restarted Blender after first install
2. If yes, manually remove the flag:
   ```bash
   rm ~/.config/blender/[VERSION]/scripts/addons/cloud_storage_data/.packages_v3
   ```
3. Restart Blender - packages will reinstall
4. Restart again

---

### Files in the list but can't download

1. Make sure you're connected (Google Drive) or credentials are correct (S3)
2. Check console for specific error messages
3. For Google Drive: Try disconnecting and reconnecting

---

### Missing textures after download

**If you download a non-zipped .blend file and textures are missing:**

1. Check the console - it shows what dependencies were downloaded:
   ```
   Downloading dependency: texture1.png
   Downloading dependency: hdri.exr
   Downloaded 5 dependency files
   ```

2. Make sure all texture/asset files are in the **same Google Drive folder** as the .blend file

3. **Best practice:** Always use the "Upload" button which packages everything as a .zip

**For collaborators sharing files:**
- Put all project files (blend + textures + assets) in the same folder
- Share the entire folder
- OR use the Upload button to create a proper zip package

---

### "Current file has no save location" error

**If you see this when trying to load a file:**

This means your current Blender file has **never been saved** (it's still "untitled").

**Solution:**
1. Click **Cancel** in the dialog
2. Save your current file first (File → Save As)
3. Then try loading the cloud file again

The addon can only auto-save files that have been saved at least once!

---

### AWS S3 Errors

#### "Access Denied" or "403 Forbidden"

**Causes:**
1. Wrong AWS credentials
2. IAM user doesn't have S3 permissions
3. Bucket is in a different region

**Solutions:**
1. **Check credentials** in preferences - make sure they're correct
2. **Verify IAM permissions**:
   - Go to IAM Console
   - Check your user has `AmazonS3FullAccess` policy
3. **Check region**: Bucket region in preferences must match actual bucket region

#### "Bucket does not exist"

**Solutions:**
1. **Check bucket name** - must be exact (case-sensitive)
2. **Verify bucket exists** in S3 console: https://s3.console.aws.amazon.com/
3. **Check region** - make sure you're using the correct region

#### "Invalid Access Key"

**Solution:**
1. Access keys might be deactivated or deleted
2. Go to IAM Console → Users → Your user → Security credentials
3. Check if access key is still active
4. If not, create a new access key and update in Blender

#### Files uploaded but don't appear in list

**Solution:**
1. Click **"Refresh"** button
2. Make sure you selected "AWS S3" in the dropdown
3. Check console for errors

---

## 9. 🔒 Privacy & Permissions

### Google Drive Permissions

The addon requests:
```
See, edit, create, and delete all of your Google Drive files
```

**Why?**
- To see your existing .blend files (not just ones uploaded via the addon)
- To access folders shared with you
- To upload and download files

**Your data:**
- ✅ Stored in YOUR Google Drive
- ✅ Only accessible by YOU
- ✅ OAuth tokens stored locally in Blender
- ✅ No data sent to any third party

### AWS S3

Your AWS credentials are stored locally in Blender preferences. Never shared.

---

## 10. 🎯 Use Cases

### Solo Artist
- **AWS S3:** Backup your work to the cloud with unlimited storage
- **Google Drive:** Access files from multiple computers (home, studio, laptop)
- Work seamlessly across locations

### Studio/Team
- **Google Drive:** Share project folders via Drive
- **AWS S3:** Central asset library with enterprise-grade storage
- Everyone can browse and load shared files

### Client Work
- **Google Drive:** Client shares reference files via Drive link
- **AWS S3:** Deliver final work through S3 signed URLs
- Load and send files directly in Blender

### Freelancer
- **AWS S3:** Store all client projects securely and cheaply
- **Google Drive:** Quick collaboration with clients who use Drive
- Access everything from anywhere

---

## 11. 💡 Best Practices

### Always Save Before Loading
**⚠️ Important:** Loading a file from the cloud will close your current Blender project.

**Best workflow:**
1. Save your current work (Ctrl+S)
2. Then load files from the cloud

**The addon will warn you** if you have unsaved changes, but it's good practice to save first!

### Use the Upload Button
When uploading projects, always use the **"Upload"** button in the addon:
- ✅ Automatically packages everything as .zip
- ✅ Includes all dependencies
- ✅ Preserves folder structure
- ✅ Easy to download and use

### Organize with Folders
Use the **"Folder ID"** feature to organize your work:
- Create folders like "Active Projects", "Archive", "Assets"
- Set the Folder ID in preferences
- All uploads go to that folder

---

## 12. 🐛 Known Issues

### Blender 3.0-3.3
- Some UI icons may look slightly different (cosmetic only)

### Large Files (>1GB)
- Upload/download may take time
- Blender might appear frozen - check console for progress
- Consider splitting very large projects

### Network Issues
- If upload/download fails, check your internet connection
- Google Drive has rate limits - wait a minute and try again

---

## 13. 📝 Technical Details

### Package Dependencies

The addon automatically installs:
- `google-auth==2.35.0`
- `google-auth-httplib2==0.2.0`
- `google-auth-oauthlib==1.2.0`
- `google-api-python-client==2.147.0`
- `boto3` (latest)

### File Format

**Upload:**
- Creates a zip file containing your .blend + all dependencies
- Preserves folder structure
- Uploads to cloud

**Download:**
- Downloads zip file
- Extracts to temp directory
- Opens .blend file
- Dependencies automatically reconnected

### Storage Location

**Addon data is stored at:**

**Windows:**
```
C:\Users\YourName\AppData\Roaming\Blender Foundation\Blender\[VERSION]\scripts\addons\cloud_storage_data\
```

**macOS:**
```
~/Library/Application Support/Blender/[VERSION]/scripts/addons/cloud_storage_data/
```

**Linux:**
```
~/.config/blender/[VERSION]/scripts/addons/cloud_storage_data/
```

**Contains:**
- `.packages_v3` - Package installation flag
- `gdrive_token.pickle` - Google Drive authentication token

---

## 14. 🔄 Updating the Addon

1. Download new version
2. Go to Blender Preferences → Add-ons
3. Remove old version
4. Install new version
5. Restart Blender
6. Reconnect to Google Drive (if credentials changed)

**Note:** Your uploaded files remain safe in the cloud.

---

## 15. 🤝 Contributing

Found a bug? Have a feature request?

- **GitHub Repository:** https://github.com/mrkuros/bloc
- **Issues:** https://github.com/mrkuros/bloc/issues
- **Author:** https://github.com/mrkuros

---

## 16. 📜 License

MIT License

Copyright (c) 2026 Kashish (MrKuros)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 17. 🎉 Quick Start Checklist

- [ ] Install addon in Blender
- [ ] **Wait for packages to install (30-60 sec freeze is normal!)**
- [ ] **Restart Blender**
- [ ] Choose Google Drive OR AWS S3
- [ ] Configure credentials
- [ ] Connect to Google Drive (if using)
- [ ] Save a .blend file
- [ ] Click "Upload"
- [ ] Click "Refresh" to see your file
- [ ] Done! 🎊

---

**Version:** 3.0  
**Release Date:** February 2026  
**Blender Compatibility:** 3.0 - 5.x+

**Happy Blending! 🎨**