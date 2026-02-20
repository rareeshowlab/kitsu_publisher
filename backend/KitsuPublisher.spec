# -*- mode: python ; coding: utf-8 -*-
import os
import platform

# 버전 정보 로딩
# spec 파일은 backend 디렉토리에서 실행될 것을 가정하거나, 실행 위치 기준으로 경로를 잡습니다.
spec_dir = os.path.dirname(os.path.abspath(SPEC))
version_path = os.path.join(spec_dir, 'version.py')
version_vars = {}
with open(version_path, 'r') as f:
    exec(f.read(), version_vars)
version = version_vars.get('VERSION', '0.0.0')

# OS 정보 파싱
system = platform.system()
if system == 'Darwin':
    os_name = 'macOS'
elif system == 'Windows':
    os_name = 'windows'
else:
    os_name = system.lower()

# 빌드 파일 이름 구성
base_name = f'KitsuPublisher_{os_name}_v{version}'

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[],
    datas=[('../frontend/build', 'frontend/build')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=base_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.icns'],
)
app = BUNDLE(
    exe,
    name=f'{base_name}.app',
    icon='icon.icns',
    bundle_identifier=None,
)
