# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['mlox/__main__.py'],
             pathex=['mlox'],
             binaries=[],
             datas=[
                 ('mlox/static/', 'mlox/static'),  # For static files
             ],
             hiddenimports=['mlox.static', 'libarchive', 'appdirs', 'PyQt5'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          # exclude_binaries=True,
          name='mlox_linux',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True , icon='mlox\\static\\mlox.ico')

