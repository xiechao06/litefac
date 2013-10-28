# -*- coding: UTF-8 -*-
"""
@author: Yangminghua
@version: $
"""
import os
import sys
import fcntl
import logging
import logging.handlers
import daemon

class FileLikeLogger:
    """wraps a logging.Logger into a file like object"""

    def __init__(self, logger):
        self.logger = logger

    def write(self, str):
        str = str.rstrip() #get rid of all tailing newlines and white space
        if str: #don't log emtpy lines
            for line in str.split('\n'):
                self.logger.critical(line) #critical to log at any logLevel

    def flush(self):
        for handler in self.logger.handlers:
            handler.flush()

    def close(self):
        for handler in self.logger.handlers:
            handler.close()



class PidFile(object):
   """Context manager that locks a pid file.  Implemented as class
   not generator because daemon.py is calling .__exit__() with no parameters
   instead of the None, None, None specified by PEP-343."""
   # pylint: disable=R0903

   def __init__(self, path):
       self.path = path
       self.pidfile = None

   def __enter__(self):
       self.pidfile = open(self.path, "a+")
       try:
           fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
       except IOError:
           raise SystemExit("Already running according to " + self.path)
       self.pidfile.seek(0)
       self.pidfile.truncate()
       self.pidfile.write(str(os.getpid()))
       self.pidfile.flush()
       self.pidfile.seek(0)
       return self.pidfile

   def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
       try:
           self.pidfile.close()
       except IOError as err:
           # ok if file was just closed elsewhere
           if err.errno != 9:
               raise
       os.remove(self.path)


def openFilesFromLoggers(loggers):
    """returns the open files used by file-based handlers of the specified
    loggers"""
    openFiles = []
    for logger in loggers:
        for handler in logger.handlers:
            if hasattr(handler, 'stream') and\
               hasattr(handler.stream, 'fileno'):
                openFiles.append(handler.stream)
    return openFiles


class LoggingDaemonContext(daemon.DaemonContext):
    def _addLoggerFiles(self):
        """adds all files related to loggers_preserve to files_preserve"""
        for logger in [self.stdout_logger, self.stderr_logger]:
            if logger:
                self.loggers_preserve.append(logger)
        loggerFiles = openFilesFromLoggers(self.loggers_preserve)
        self.files_preserve.extend(loggerFiles)

    def __init__(self, chroot_directory=None, working_directory='/', umask=0,
                 uid=None, gid=None, prevent_core=True, detach_process=None,
                 files_preserve=None, loggers_preserve=None, pidfile=None,
                 stdout_logger=None, stderr_logger=None, signal_map=None):
        if not loggers_preserve: loggers_preserve = []
        if not files_preserve: files_preserve = []
        self.stdout_logger = stdout_logger
        self.stderr_logger = stderr_logger
        self.loggers_preserve = loggers_preserve

        devnull_in = open(os.devnull, 'r+')
        devnull_out = open(os.devnull, 'w+')
        files_preserve.extend([devnull_in, devnull_out])

        daemon.DaemonContext.__init__(self,
                                      chroot_directory=chroot_directory,
                                      working_directory=working_directory,
                                      umask=umask,
                                      uid=uid,
                                      gid=gid,
                                      prevent_core=prevent_core,
                                      detach_process=detach_process,
                                      files_preserve=files_preserve,
                                      pidfile=pidfile,
                                      stdin=devnull_in,
                                      stdout=devnull_out,
                                      stderr=devnull_out,
                                      signal_map=signal_map)

    def open(self):
        self._addLoggerFiles()
        daemon.DaemonContext.open(self)
        if self.stdout_logger:
            fileLikeObj = FileLikeLogger(self.stdout_logger)
            sys.stdout = fileLikeObj
        if self.stderr_logger:
            fileLikeObj = FileLikeLogger(self.stderr_logger)
            sys.stderr = fileLikeObj

    @classmethod
    def getRotFileLogger(cls, name, filePath, logLevel=logging.DEBUG, format=None):
        format = format or '%(message)s'
        my_logger = logging.getLogger(name)
        my_logger.setLevel(logLevel)
        handler = logging.handlers.RotatingFileHandler(
                      filePath, maxBytes=2000, backupCount=2)
        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)
        my_logger.addHandler(handler)
        return my_logger