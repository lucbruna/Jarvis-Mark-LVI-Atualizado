[app]
title = Mark LVI
package.name = marklvi
package.domain = com.fatihmakes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,md
version = 1.0.0
requirements = python3,kivy,requests,numpy,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a,armeabi-v7a
p4a.bootstrap = sdl2
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

[buildozer]
log_level = 2
warn_on_root = 1
PY