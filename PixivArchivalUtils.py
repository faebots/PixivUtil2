import codecs
import datetime
import gc
import getpass
import os
import platform
import re
import subprocess
import sys
from optparse import OptionParser
import rich

import PixivArtistHandler
import PixivBatchHandler
import PixivBookmarkHandler
import PixivBrowserFactory
import PixivConfig
import PixivConstant
import PixivFanboxHandler
import PixivHelper
import PixivImageHandler
import PixivListHandler
import PixivModelFanbox
import PixivSketchHandler
import PixivNovelHandler
import PixivTagsHandler
import PixivSearchHandler
from PixivDBManager import PixivDBManager
from PixivException import PixivException
from PixivTags import PixivTags

script_path = PixivHelper.module_path()

op = ''
ERROR_CODE = 0
UTF8_FS = None

__use_menu = False

__config__ = PixivConfig.PixivConfig()
configfile = "config.ini"
__dbManager__ = None
__br__ = None
__blacklistTags = list()
__suppressTags = list()
__log__ = PixivHelper.get_logger()
__errorList = list()
__blacklistMembers = list()
__blacklistTitles = list()
__valid_options = ()
__seriesDownloaded = []

start_iv = False
dfilename = ""

def no_menu():
    search_related_tags()
    return 0

def print_related_tags(tag_list):
    tag_list = dict(tag_list)
    sorted_tags = sorted(tag_list.keys, key=tag_list.get, reverse=True)
    for tag in sorted_tags:
        print(f"{tag} - {tag_list[tag]}")

def search_related_tags():
    print("1 - Search by tag(s)")
    print("2 - Search by Title/Caption")
    search_type = input().rstrip("\r")
    search = input("Search terms: ").rstrip("\r")
    (page, end_page) = PixivHelper.get_start_and_end_number()
    (start_date, end_date) = PixivHelper.get_start_and_end_date()
    title_caption = (search_type == "2")
    if not title_caption:
        wildcard = input("Use partial tag matching? (y/n) ").upper() == "Y"
    else:
        wildcard = True
    PixivSearchHandler.search(__config__,
                              search,
                              page=page,
                              end_page=end_page,
                              wild_card=wildcard,
                              title_caption=title_caption,
                              start_date=start_date,
                              end_date=end_date,
                              process=PixivSearchHandler.SearchType.LIST_ONLY)


def main_loop():
    global __errorList
    global ERROR_CODE
    global __use_menu
    if __use_menu:
        while True:
            try:
                if len(__errorList) > 0:
                    print("Unknown errors from previous operation")
                    for err in __errorList:
                        message = err["type"] + ": " + str(err["id"]) + " ==> " + err["message"]
                        PixivHelper.print_and_log('error', message)
                    __errorList = list()
                    ERROR_CODE = 1
                selection = menu()
            except KeyboardInterrupt:
                PixivHelper.print_and_log("info", f"Keyboard Interrupt pressed, selection: {selection}")
                PixivHelper.clearScreen()
                print("Restarting...")
                selection = menu()
            except PixivException as ex:
                if ex.htmlPage is not None:
                    filename = f"Dump for {PixivHelper.sanitize_filename(ex.value)}.html"
                    PixivHelper.dump_html(filename, ex.htmlPage)
                raise  # keep old behaviour

    else:
        no_menu()

def menu():
    return '1'

def doLogin(password, username):
    global __br__
    result = False
    # store username/password for oAuth in case not stored in config.ini
    if username is not None and len(username) > 0:
        __br__._username = username
    if password is not None and len(password) > 0:
        __br__._password = password

    try:
        if len(__config__.cookie) > 0:
            result = __br__.loginUsingCookie()

        if not result:
            result = __br__.login(username, password)

    except BaseException:
        PixivHelper.print_and_log('error', f'Error at doLogin(): {sys.exc_info()}')
        raise PixivException("Cannot Login!", PixivException.CANNOT_LOGIN)
    return result

def main():
    global configfile
    global __br__
    global dfilename
    global op
    global ERROR_CODE
    global __dbManager__
    global __valid_options

    try:
        __config__.loadConfig(path=configfile)
        PixivHelper.set_config(__config__)
    except BaseException:
        PixivHelper.print_and_log("error", f'Failed to read configuration from {configfile}.')

    try:
        __dbManager__ = PixivDBManager(root_directory=__config__.rootDirectory, target=__config__.dbPath)
        __dbManager__.createDatabase()

        PixivHelper.set_log_level(__config__.logLevel)
        if __br__ is None:
            __br__ = PixivBrowserFactory.getBrowser(config=__config__)
        if __config__.useLocalTimezone:
            PixivHelper.print_and_log("info", f"Using local timezone: {PixivHelper.LocalUTCOffsetTimezone()}")

        username = __config__.username
        if username == '':
            username = input('Username ? ').rstrip("\r")
        else:
            msg = f'Using Username: {username}'
            PixivHelper.print_and_log('info', msg)

        password = __config__.password
        if password == '':
            password = getpass.getpass('Password ? ')

        result = doLogin(password, username)

        if result:
            main_loop()
        else:
            ERROR_CODE = PixivException.NOT_LOGGED_IN

    except PixivException as pex:
        PixivHelper.print_and_log('error', pex.message)
        ERROR_CODE = pex.errorCode
    except Exception as ex:
        if __config__.logLevel == "DEBUG":
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            __log__.exception('Unknown Error: %s', str(exc_value))
        PixivHelper.print_and_log("error", f"Unknown Error, please check the log file: {sys.exc_info()}")
        ERROR_CODE = getattr(ex, 'errorCode', -1)
    finally:
        __dbManager__.close()
        __log__.setLevel("INFO")
        __log__.info('EXIT: %s', ERROR_CODE)
        __log__.info('###############################################################')
        sys.exit(ERROR_CODE)

    return

def get_related_tags(search, search_type):
    return

if __name__ == '__main__':
    main()