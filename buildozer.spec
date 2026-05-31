[app]
# (str) Title of your application
title = StockVibe Mobile

# (str) Package name
package.name = stockvibe

# (str) Package domain (needed for Android packaging)
package.domain = org.stockvibe

# (str) Source code where the main.py is located
source.dir = .

# (list) Source file extensions to include
source.include_exts = py,kv,db,txt

# (str) Application versioning
version = 1.0

# (list) Application requirements
requirements = python3,kivy

# (str) Supported orientations
orientation = portrait

# (list) Android architectures to build for
android.arch = armeabi-v7a, arm64-v8a

# (str) Presplash picture
presplash.filename = 

# (str) Icon of the application
icon.filename = 

# (list) Permissions
android.permissions = INTERNET

# (str) Android API level
android.api = 33

# (str) Buildozer log level
log_level = 2
