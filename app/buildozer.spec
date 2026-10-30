[app]
title = Учёт локомотивов
package.name = locoapp
package.domain = org.depot
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy==2.3.0,kivymd==1.1.1,pillow,Cython==0.29.34,pyjnius==1.6.1,setuptools,wheel
orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1