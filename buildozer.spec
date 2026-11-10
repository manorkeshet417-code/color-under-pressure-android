[app]
title = Color Under Pressure
package.name = colorunderpressure
package.domain = studio.manstudio
source.dir = app
source.include_exts = py,mp3,ogg,wav,png,jpg,ttf,json
# version is set by the build (GAME_VERSION in color_rush.py + build number)
version = 2.2.2
requirements = python3,pygame,pyjnius,android,certifi
icon.filename = icon.png
presplash.filename = presplash.png
android.presplash_color = #0A0A14
orientation = landscape
fullscreen = 1
android.permissions = INTERNET,ACCESS_NETWORK_STATE,VIBRATE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.release_artifact = apk
android.allow_backup = True
p4a.bootstrap = sdl2
p4a.branch = v2024.01.21
p4a.local_recipes = ./recipes

[buildozer]
log_level = 2
warn_on_root = 0
