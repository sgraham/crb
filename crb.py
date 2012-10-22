#!/usr/bin/env python

import os
import re
import shutil
import sys


_g_repo = 'pristine'
_g_processed = 'crb'


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
  os.system('rmdir /s/q %s' % path)


def PullSource():
  print 'Updating source...'
  RemoveTree(_g_processed)
  if os.path.exists(_g_repo):
    # TODO: Should confirm it's the right repo.
    Run('cd %s && git pull -q' % _g_repo)
  else:
    Run('git clone -q http://git.chromium.org/chromium/src/base.git %s' %
        _g_repo)
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
              'nix\\', 'xdg_',
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


def TestCompilation(file_list):
  print 'Testing compilation...'
  RemoveTree('build')
  os.makedirs('build')
  olddir = os.getcwd()
  os.chdir('build')
  Run('cl /W4 /WX /DUNICODE /D_UNICODE /DNOMINMAX /D_CRT_SECURE_NO_WARNINGS '
      '/DWIN32_LEAN_AND_MEAN /DWIN32 /D_WIN32 /D_CRT_RAND_S '
      '/I.. /wd4530 /wd4310 /wd4127 /wd4100 /wd4481 /wd4244 /wd4245 /wd4996 '
      '/wd4702 /wd4018 /wd4706 /wd4355 /wd4512 /wd4800 /wd4701 '
      '/wd4189 /wd4554 ' # TODO These should both be removed.
      '/MP /c /nologo %s' % (
    ' '.join((os.path.join('..', _g_processed, x) for x in file_list))))
  os.chdir(olddir)


def main(args):
  CheckForTools()
  PullSource()
  all_files = GetFileList()
  TextualReplacements(all_files)
  win_lib = FilterFileList(all_files, ('win', 'lib'))
  TestCompilation(win_lib)

if __name__ == '__main__':
  sys.exit(main(sys.argv))