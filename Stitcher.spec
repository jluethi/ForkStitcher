# -*- mode: python -*-

block_cipher = None


a = Analysis(['fork-stitcher\\Stitcher.py'],
             pathex=['fork-stitcher', 'Z:\\home\\j.luethi\\ForkStitcher'],
             binaries=[],
             datas=[('C:\\Users\\j.luethi\\AppData\\Local\\Continuum\\miniconda3\\envs\\fork_stitcher\\share\\pyjnius\\pyjnius.jar', '.\\share\\pyjnius'), ('Z:\\home\\j.luethi\\Downloads\\OpenJDK8U-jdk_x64_windows_hotspot_8u212b04\\jdk8u212-b04', '.\\share\\jdk8'), ('Z:\\home\\j.luethi\\Downloads\\apache-maven-3.6.1-bin\\apache-maven-3.6.1', '.\\share\\maven')],
             hiddenimports=[],
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
          [],
          exclude_binaries=True,
          name='Stitcher',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True , icon='stitchericon_1_EYC_icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Stitcher')
