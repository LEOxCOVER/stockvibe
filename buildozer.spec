[app]
title = StockVibe Mobile
package.name = stockvibe
package.domain = org.stockvibe

source.dir = .
source.main = main_android.py
source.include_exts = py,kv,json,txt
source.include_patterns = stockvibe_config.example.json
source.exclude_dirs = .venv,.git,build,dist,bin,.buildozer,backend,web,.vscode

version = 1.1.0

requirements = python3,kivy,pyjnius,android

orientation = portrait

android.archs = arm64-v8a,armeabi-v7a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.accept_sdk_license = True
android.allow_backup = True

log_level = 2

[buildozer]
log_level = 2
warn_on_root = 0
