#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ftplib
import threading
import re
import datetime



class FTPExt(ftplib.FTP_TLS):
    """Extensions to the 'ftplib' standard library.
    Features include:
    X-DUPE support.
    Stat -L directory listing support.
    FXP-support CPSV/PSV.
    Logging and other useful features, have a look yourself.
    
    I've made the getter functions thread-safe to make multiple objects
    easier to handle.
    It inherits from ftplib.FTP_TLS which means that it supports
    AUTH TLS and Clear Text, which to use is specified when the object is
    initialized.

    mode by zengqb
    """
    def __init__(self, host, port, user, password, use_ssl=False,
                 use_log=False, debug=0):
        self.lock = threading.Lock()
        self.port = port
        self.debugging = debug
        if use_log:
            self._log = ''
        self.use_log = use_log
        self._last_response = ''
        self._last_command = ''
        self.use_pret = False
        self.use_xdupe = False
        self._xdupes = []
        self.use_ssl = use_ssl
        if self.use_ssl:
            ftplib.FTP_TLS.__init__(self, host, user, password)
        else:
            self.keyfile = None
            self.certfile = None
            self.context = None
            self._prot_p = False
            ftplib.FTP.__init__(self, host, user, password)

    @property
    def last_response(self):
        """The last response received from the server."""
        with self.lock:
            return self._last_response

    @property
    def last_command(self):
        """The last command that was sent to the server."""
        with self.lock:
            return self._last_command

    @property
    def xdupes(self):
        """List of dupes, if X-DUPE is enabled then each time the \
        server returns an 553 (X-DUPE) response this variable will be \
        populated with the dupe filenames"""
        with self.lock:
            return self.xdupes

    @property
    def log(self):
        """Log with all server communication"""
        with self.lock:
            if self._log[0] == '\n':
                self._log = self._log[1:]
            return self._log

    # Internal: The angle brackets are useless annoying for some added features
    def _sanitize(self, line):
        if line[:5] in {'pass ', 'PASS '}:
            i = len(line.rstrip('\r\n'))
            line = line[:5] + '*'*(i-5) + line[i:]
        return repr(line.strip('\n\r'))[1:-1]

    # Internal: Made sure it wont try auth TLS when self.use_ssl is false
    def login(self, user='', passwd='', acct=''):
        if self.use_ssl and not isinstance(self.sock, ftplib.ssl.SSLSocket):
            self.auth()
        return ftplib.FTP.login(self, user, passwd, acct)

    # Internal: Added logging capabilities and last response
    def getline(self):
        line = self.file.readline(self.maxline + 1)
        if len(line) > self.maxline:
            raise ftplib.Error("got more than %d bytes" % self.maxline)
        if self.debugging > 1:
            print('*get*', self.sanitize(line))
        if self.use_log:
            with self.lock:
                self._log = (self._log +
                             ('\n*get* {0}'.format(self._sanitize(line))))
        with self.lock:
            self._last_response = self._sanitize(line)
        if not line:
            raise EOFError
        if line[-2:] == ftplib.CRLF:
            line = line[:-2]
        elif line[-1:] in ftplib.CRLF:
            line = line[:-1]
        return line

    # Internal:  Added xdupe support
    def getresp(self):
        resp = self.getmultiline()
        if self.debugging:
            print('*resp*', self.sanitize(resp))
        self.lastresp = resp[:3]
        c = resp[:1]
        if c in {'1', '2', '3'}:
            return resp
        if c == '4':
            raise ftplib.error_temp(resp)
        if c == '5':
            if self.lastresp == '553' and self.use_xdupe:
                with self.lock:
                    self.parse_xdupe(resp)
            raise ftplib.error_perm(resp)
        raise ftplib.error_proto(resp)

    # Internal: Added support for pret
    def ntransfercmd(self, cmd, rest=None):
        if self.use_pret:
            self.voidcmd('PRET ' + cmd)
        return ftplib.FTP_TLS.ntransfercmd(self, cmd, rest)

    # Internal: get dupe filenames from 553 (xdupe) response
    def parse_xdupe(self, resp):
        self._xdupes = []
        """Contains dupes from last X-DUPE response"""
        for d in resp.split('\n'):
            m = re.search('X-DUPE: (.+\.[\w\d]{3,4})', d)
            if m:
                self._xdupes.append(m.group(1))

    # Internal: Added logging capabilities and last command
    def putline(self, line):
        with self.lock:
            self._last_command = self._sanitize(line)
        if self.use_log:
            with self.lock:
                self._log = (self._log +
                             ('\n*put* {0}'.format(self._sanitize(line))))
        ftplib.FTP_TLS.putline(self, line)

    def enable_pret(self):
        """Enable pre transfer support
        http://www.drftpd.org/index.php/PRET_Specifications"""
        self.use_pret = True

    def disable_pret(self):
        """Disable pre transfer support.
        http://www.drftpd.org/index.php/PRET_Specifications"""
        self.use_pret = False

    def enable_xdupe(self):
        """Enable X-DUPE support.
        http://www.smartftp.com/static/Products/SmartFTP/RFC/x-dupe-info.txt"""
        self.voidcmd('SITE XDUPE 3')
        self.use_xdupe = True

    def disable_xdupe(self):
        """Enable X-DUPE support.
        http://www.smartftp.com/static/Products/SmartFTP/RFC/x-dupe-info.txt"""
        self.voidcmd('SITE XDUPE 0')
        self.use_xdupe = False

    def ls(self):
        """Get directory list via STAT -L command.
        Returns a dict where the keys are the filenames and the value
        is information about the file/directory."""
        lines = self.voidcmd('STAT -L')
        dir_list = {}
        for line in lines.split('\n'):
            file_info = self.parse_ls(line)
            if file_info:
                dir_list[file_info[0]] = file_info[1]
        return dir_list

    # Internal: Get file information from supplied line, should
    # be part of a 213 (stat -l) response
    def parse_ls(self, line):
        try:
            m = self.rg.search(line)
        except:
            rg_txt = ('([pbcdlfmpSs-])' +
                      '(((r|-)(w|-)([xsStTL-]))((r|-)(w|-)' +
                      '([xsStTL-]))((r|-)(w|-)([xsStTL-])))\+?\s+' +
                      '(\d+)\s+(\S+)\s+' +
                      '(?:(\S+(?:\s\S+)*)\s+)?' + '(?:\d+,\s+)?' +
                      '(\d+)\s+' +
                      '((?:\d+[-/]\d+[-/]\d+)|(?:\S+\s+\S+))\s+' +
                      '(\d+(?::\d+)?)\s+(\S*)(\s*.*)')
            self.rg = re.compile(rg_txt, re.DOTALL)
            m = self.rg.search(line)
        if not m:
            return None
        dir, symlink, file, device = False, False, False, False
        if re.search('d', m.group(1)):
            dir = True
        elif re.search('l', m.group(1)):
            symlink = True
        elif re.search('[f-]', m.group(1)):
            file = True
        elif re.search('[psbc]', m.group(1)):
            symlink = True
        else:
            return False
        user = m.group(16).strip()
        ftptime = self._timeConvert(m.group(19).strip(), m.group(20).strip())
        filesize = int(m.group(18))
        basename = m.group(21).strip()
        if m.group(22):
            basename = basename + m.group(22)
        if symlink:  # Remove where the symlink is pointing, it's not needed
            basename = basename.split(' -> ')[0]
        if basename == '.' or basename == '..':
            return None
        return basename, {
            'dir': dir,
            'file': file,
            'device': device,
            'symlink': symlink,
            'filesize': filesize,
            'user': user,
            'ftptime':ftptime
        }

    def _timeConvert(self,d,t):
        if t.find(':') > 0 :
            y = str(datetime.date.today().year)
        else :
            y = t
            t = '00:00'
        if d.find(' ') > 0 :
            l = d.replace('  ',' ').split(' ')
            l.insert(0,y)
            d = '-'.join(l)
        return d +' ' + t
 

    def fxp_to(self, file, target, target_file=None, type='I'):
        """FXP (server-to-server-copy) a file between 2 servers."""
        if not target_file:
            target_file = file
        type = 'TYPE ' + type
        self.voidcmd(type)
        target.voidcmd(type)
        if self.use_pret:
            self.voidcmd('PRET RETR ' + file)
        host, host_port = ftplib.parse227(self.sendcmd('PASV'))
        if target.use_pret:
            target.voidcmd('PRET STOR' + target_file)
        target.sendport(host, host_port)
        t_reply = target.sendcmd('STOR ' + target_file)
        if t_reply[:3] not in {'125', '150'}:
            raise ftplib.error_proto  # RFC 959
        reply = self.sendcmd('RETR ' + file)
        if reply[:3] not in {'125', '150'}:
            raise ftplib.error_proto  # RFC 959
        self.voidresp()
        target.voidresp()

    def secure_fxp_to(self, file, target, target_file=None, type='I'):
        """FXP (server-to-server-copy) a file between 2 servers. This uses
        CPSV instead of PASV to fxp file with SSL encryption"""
        if not target_file:
            target_file = file
        if not self.prot_p:
            self.prot_p()
        if not target.prot_p:
            target.prot_p()
        type = 'TYPE ' + type
        self.voidcmd(type)
        target.voidcmd(type)
        if self.use_pret:
            self.voidcmd('PRET RETR ' + file)
        host, host_port = ftplib.parse227(self.sendcmd('CPSV'))
        if target.use_pret:
            target.voidcmd('PRET STOR' + target_file)
        target.sendport(host, host_port)
        t_reply = target.sendcmd('STOR ' + target_file)
        if t_reply[:3] not in {'125', '150'}:
            raise ftplib.error_proto  # RFC 959
        reply = self.sendcmd('RETR ' + file)
        if reply[:3] not in {'125', '150'}:
            raise ftplib.error_proto  # RFC 959
        self.voidresp()
        target.voidresp()
