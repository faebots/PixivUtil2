import gc
import http.client
import os
import sys
import time
from enum import Enum

import PixivBrowserFactory
import PixivConstant
import PixivHelper
import PixivImageHandler
import PixivImage


class SearchType(Enum):
    LIST_ONLY = 0
    DOWNLOAD_ALL = 1
    WEB_REPRINT_ARCHIVE = 2

def process_image(
    image,
    process_option
):
    return

def search(
    config,
    search,
    page=1,
    end_page=0,
    wild_card=True,
    title_caption=False,
    start_date=None,
    end_date=None,
    sort_order='date_d',
    type_mode=None,
    notifier=None,
    process=SearchType.LIST_ONLY
):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    search_page = None
    _last_search_result = None
    i = page
    updated_limit_count = 0
    related_tags = dict()
    artist_result_list = dict()
    image_result_list = []
    
    search_tags = PixivHelper.decode_tags(search)
    search = PixivHelper.encode_tags(search)
    if title_caption:
        current_search_tags = []
    else:
        current_search_tags = [t.strip("-()") for t in search_tags.split() if t != "OR"]

    try:

        images = 1
        last_image_id = -1
        skipped_count = 0
        offset = 60
        start_offset = (page - 1) * offset
        stop_offset = end_page * offset
        
        PixivHelper.print_and_log('info', f'Searching for: ({search_tags}) {search}')
        flag = True
        while flag:
            (t, search_page) = PixivBrowserFactory.getBrowser().getSearchTagPage(search,
                                                                                 i,
                                                                                 wild_card=wild_card,
                                                                                 title_caption=title_caption,
                                                                                 start_date=start_date,
                                                                                 end_date=end_date,
                                                                                 sort_order=sort_order,
                                                                                 start_page=page,
                                                                                 type_mode=type_mode)
            if len(t.itemList) == 0:
                PixivHelper.print_and_log(None, 'No more images')
                flag = False
            elif _last_search_result is not None:
                set1 = set((x.imageId) for x in _last_search_result.itemList)
                difference = [x for x in t.itemList if (x.imageId) not in set1]
                if len(difference) == 0:
                    PixivHelper.print_and_log(None, 'Getting duplicated result set, no more new images.')
                    flag = False
            
            if flag:
                for item in t.itemList:
                    last_image_id = item.image_id
                    result = 0
                    while True:
                        try:
                            if t.availableImages > 0:
                                total_image = t.availableImages
                                if(stop_offset > 0 and stop_offset < total_image):
                                    total_image = stop_offset
                                total_image = total_image - start_offset
                            else:
                                total_image = ((i - 1) * 20) + len(t.itemList)
                            result = PixivConstant.PIXIVUTIL_OK
                            (image, parse_medium_page) = PixivBrowserFactory.getBrowser().getImagePage(image_id=last_image_id,
                                                                                                       image_response_count=item.imageResponse)
                            image_result_list.append(image)
                            if image.artist.artistId in artist_result_list:
                                artist_result_list[image.artist.artistId] += 1
                            else:
                                artist_result_list[image.artist.artistId] = 1
                            for x in image.tags:
                                if x.tag not in current_search_tags:
                                    if x.tag in related_tags:
                                        related_tags[x.tag] += 1
                                    else:
                                        related_tags[x.tag] = 1
                            process_image(image, process)
                            PixivHelper.wait(result, config)
                            break
                        except KeyboardInterrupt:
                            result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                            break
                        except http.client.BadStatusLine:
                            PixivHelper.print_and_log(None, "Stuff happened, trying again after 2 second...")
                            time.sleep(2)
                    images = images + 1
                    if result in (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                                  PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER,
                                  PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT):
                        updated_limit_count = updated_limit_count + 1
                        gc.collect()
                        continue
                    elif result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                        choice = input("Keyboard Interrupt detected, continue to next image (Y/N)").rstrip("\r")
                        if choice.upper() == 'N':
                            PixivHelper.print_and_log("info", f"Tags: {search}, processing aborted.")
                            flag = False
                            break
                        else:
                            continue
            PixivBrowserFactory.getBrowser().clear_history()

            i = i + 1
            _last_search_result = t

            if end_page != 0 and end_page < i:
                PixivHelper.print_and_log('info', f"End Page reached: {end_page}")
                flag = False
            if t.isLastPage:
                PixivHelper.print_and_log('info', f"Last page: {i - 1}")
                flag = False

            PixivHelper.print_and_log(None, 'done')
            if search_page is not None:
                del search_page
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', f'Error at process_tags() at page {i}: {sys.exc_info()}')
        try:
            if search_page is not None:
                dump_filename = f'Error page for search tags {tags} at page {i}.html'
                PixivHelper.dump_html(dump_filename, search_page)
                PixivHelper.print_and_log('error', f"Dumping html to: {dump_filename}")
        except BaseException:
            PixivHelper.print_and_log('error', f'Cannot dump page for search tags: {search_tags}')
        raise
    finally:
        return (related_tags, image_result_list, artist_result_list)