#!/usr/bin/env python

import os
import re
import shutil
import sys


_g_repo = 'pristine'
_g_processed = 'crb'
# TODO: Command line flag to set to 'master' for updating or saucyness.
_g_lkg = 'c5a2c1cd93b1cb9f38d84d1c6343e3be90aceee1'

def Run(command, message=None):
  if os.system(command) != 0:
    if not message:
      message = "'%s' failed." % command
    raise SystemExit(message)


def CheckForTools():
  """Make sure all required command line tools are in the PATH and are recent
  versions."""
  # git.
  Run('git --version > nul', '`git\' not found in PATH.')

  # Win8 SDK
  Run('cl /Zs windows_8_sdk_required_test.c /nologo',
      "Either `cl' not found in PATH, or it isn't set to use Windows 8 SDK.")


def RemoveTree(path):
  # shutil.rmtree dies on read-only files. wtf.
  os.system('rmdir /s/q %s >nul 2>nul' % path)


def PullSource():
  print 'Updating source...'
  RemoveTree(_g_processed)
  if os.path.exists(_g_repo):
    # TODO: Should confirm it's the right repo.
    Run('cd %s && git checkout -q master && git pull -q' % _g_repo)
  else:
    Run('git clone -q http://git.chromium.org/chromium/src/base.git %s' %
        _g_repo)
  Run('cd %s && git checkout -q %s' % (_g_repo, _g_lkg))
  shutil.copytree(_g_repo, _g_processed)
  RemoveTree(os.path.join(_g_processed, '.git'))
  shutil.copy('misc/build_config.h', _g_processed)
  shutil.copy('misc/gtest_prod.h', _g_processed)


def SubBaseToCrbInInclude(file):
  lines = open(file, 'rU').read().splitlines(True)
  lines = [re.sub('^#include "base/', '#include "crb/', x) for x in lines]
  open(file, 'wb').write(''.join(lines))


def RemoveBuildFromBuildConfig(file):
  lines = open(file, 'rU').read().splitlines(True)
  lines = [re.sub('^#include "build/build_config.h"',
                  '#include "crb/build_config.h"', x) for x in lines]
  open(file, 'wb').write(''.join(lines))


def FixPathToGtestProd(file):
  lines = open(file, 'rU').read().splitlines(True)
  lines = [re.sub('^#include "testing/gtest/include/gtest/gtest_prod.h"$',
                  '#include "crb/gtest_prod.h"', x) for x in lines]
  open(file, 'wb').write(''.join(lines))


def TextualReplacements(all_files):
  print 'Munging...'
  for name in all_files:
    file = os.path.join(_g_processed, name)
    if file.endswith('.cc') or file.endswith('.c') or file.endswith('h'):
      SubBaseToCrbInInclude(file)
      RemoveBuildFromBuildConfig(file)
      FixPathToGtestProd(file)


def GetFileList():
  all_files = []
  orig = os.getcwd()
  os.chdir(_g_processed)
  for path, dirs, files in os.walk('.'):
    if os.path.normpath(path).startswith('.git'):
      continue
    for file in files:
      all_files.append(os.path.normpath(os.path.join(path, file)))
  os.chdir(orig)
  return all_files


def FilterFileList(all_files, for_types):
  print 'Getting file list...'
  result = all_files[:]
  if 'win' in for_types:
    for x in ('_posix', '_mac', '_android', '_linux', '_ios', '_solaris',
              '.java', '_gcc', '.mm', 'android\\', '_libevent', 'chromeos\\',
              'data\\', '_freebsd', '_nacl', 'linux_', '_glib', '_gtk', 'mac\\',
              'unix_', 'file_descriptor', '_aurax11', 'sha1_win.cc', '_openbsd',
              'xdg_mime', '_kqueue', 'symbolize', 'string16.cc', '_chromeos',
              'nix\\', 'xdg_', 'file_path_watcher_stub.cc', 'dtoa.cc',
              'event_recorder_stubs.cc',
              'allocator\\', # Kind of overly involved for user-configuration.
              'i18n\\', # Requires icu (I think)
              ):
      result = [y for y in result if x not in y]
  if 'lib' in for_types:
    for x in ('README', 'LICENSE', 'OWNERS', '.h', '.patch', 'unittest',
              'PRESUBMIT', 'DEPS', '.gyp', '.py', '.isolate', '.nc', 'test\\',
              '_browsertest.cc', 'base64.cc' # TEMP
              ):
      result = [y for y in result if x not in y]
  return result


def BuildLibs(file_list):
  extra_cl_flags_for_style = {
      'debug': '/Zi /Od /D_DEBUG',
      'release': '/GL /Ox /Zi /DNDEBUG',
  }
  extra_lib_flags_for_style = {
      'debug': '',
      'release': '/LTCG',
  }
  styles = ('debug', 'release')
  def style_to_lib(s):
    return 'crb_%s.lib' % s
  for style in styles:
    intermediate_dir = style + '_obj'
    RemoveTree(intermediate_dir)
    os.makedirs(intermediate_dir)
    olddir = os.getcwd()
    os.chdir(intermediate_dir)
    shared = (
        'cl /W4 /WX /DUNICODE /D_UNICODE /DNOMINMAX /D_CRT_SECURE_NO_WARNINGS '
        '/DWIN32_LEAN_AND_MEAN /DWIN32 /D_WIN32 /D_CRT_RAND_S '
        '/I.. /wd4530 /wd4310 /wd4127 /wd4100 /wd4481 /wd4244 /wd4245 /wd4996 '
        '/wd4702 /wd4018 /wd4706 /wd4355 /wd4512 /wd4800 /wd4701 '
        '/MP /c /nologo %s' % (
          ' '.join((os.path.join('..', _g_processed, x) for x in file_list))))
    Run(shared + ' ' + extra_cl_flags_for_style[style])
    objs = ' '.join(os.path.splitext(os.path.split(x)[1])[0] + '.obj'
                    for x in file_list)
    Run('lib /nologo /out:..\\%s %s %s' % (
        style_to_lib(style), objs, extra_lib_flags_for_style[style]))
    os.chdir(olddir)
  print
  print 'Built %s.' % ', '.join(style_to_lib(s) for s in styles)


def main(args):
  CheckForTools()
  PullSource()
  all_files = GetFileList()
  TextualReplacements(all_files)
  win_lib = FilterFileList(all_files, ('win', 'lib'))
  BuildLibs(win_lib)
  print 'Headers in crb/, include path should be %s' % os.path.abspath('.')

if __name__ == '__main__':
  sys.exit(main(sys.argv))
