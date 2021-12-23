#!/usr/bin/env python3
from youtube_dl import YoutubeDL
import requests, os, json, time
import youtube_dl

class YoutubeDL(YoutubeDL):
    def get_playlist(self, url, lenv=100):
        ies = self._ies

        for ie in ies:
            if not ie.suitable(url):
                continue

            ie = self.get_info_extractor(ie.ie_key())

            if not ie.working():
                self.report_warning('The program functionality for this site has been marked as broken, '
                                    'and will probably not work.')

            videos = self.___extract_info(url, ie, {}, True)
            temp = []
            for i in videos:
                if len(temp) > lenv:
                    return temp

                temp.append(i["url"])

            return temp
        else:
            self.report_error('no suitable InfoExtractor for URL %s' % url)

    def ___extract_info(self, url, ie, extra_info, process):
        ie_result = ie.extract(url)
        if ie_result is None:  # Finished already (backwards compatibility; listformats and friends should be moved here)
            return
        if isinstance(ie_result, list):
            # Backwards compatibility: old IE result format
            ie_result = {
                '_type': 'compat_list',
                'entries': ie_result,
            }
        self.add_default_extra_info(ie_result, ie, url)
        if process:
            return self._process_ie_result(ie_result, extra_info)
        else:
            return ie_result

    def _process_ie_result(self, ie_result, download=False, extra_info={}):
        result_type = ie_result.get('_type', 'video')

        if result_type in ('url', 'url_transparent'):
            ie_result['url'] = sanitize_url(ie_result['url'])
            extract_flat = self.params.get('extract_flat', False)
            if ((extract_flat == 'in_playlist' and 'playlist' in extra_info)
                    or extract_flat is True):
                self.__forced_printings(
                    ie_result, self.prepare_filename(ie_result),
                    incomplete=True)
                return ie_result

        webpage_url = ie_result['webpage_url']
        self._playlist_level += 1
        self._playlist_urls.add(webpage_url)
        return self.___process_playlist(ie_result)


    def ___process_playlist(self, ie_result):
        playlist = ie_result.get('title') or ie_result.get('id')

        self.to_screen('[download] Downloading playlist: %s' % playlist)

        playlist_results = []

        playliststart = self.params.get('playliststart', 1) - 1
        playlistend = self.params.get('playlistend')
        # For backwards compatibility, interpret -1 as whole list
        if playlistend == -1:
            playlistend = None

        playlistitems_str = self.params.get('playlist_items')
        playlistitems = None
        if playlistitems_str is not None:
            def iter_playlistitems(format):
                for string_segment in format.split(','):
                    if '-' in string_segment:
                        start, end = string_segment.split('-')
                        for item in range(int(start), int(end) + 1):
                            yield int(item)
                    else:
                        yield int(string_segment)
            playlistitems = orderedSet(iter_playlistitems(playlistitems_str))

        ie_entries = ie_result['entries']
        return ie_entries

    def __handle_extraction_exceptions(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                raise

        return wrapper

    @__handle_extraction_exceptions
    def __extract_info(self, url, ie, download, extra_info, process):
        ie_result = ie.extract(url)
        if ie_result is None:  # Finished already (backwards compatibility; listformats and friends should be moved here)
            return
        if isinstance(ie_result, list):
            # Backwards compatibility: old IE result format
            ie_result = {
                '_type': 'compat_list',
                'entries': ie_result,
            }
        self.add_default_extra_info(ie_result, ie, url)
        if process:
            return self.process_ie_result(ie_result, download, extra_info)
        else:
            return ie_result

chars = "0123456789 abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
ydl = YoutubeDL({"quiet": True})
host = "http://localhost:5279"
titles = []

def fetch_videos(url:str)-> list:
    channel_v = url.split("/")[:5]
    channel_v.append("videos")
    channel_v = "/".join(channel_v)
    videos = ydl.get_playlist(channel_v)
    video_data = {}

    for video in videos:
        video = f"https://www.youtube.com/watch?v={video}"
        print(f"Looking at {video}")
        while True:
            try:
                data = ydl.extract_info(video, download = False)
                break
            except Exception as e:
                time.sleep(60)


        if is_uploaded(data["title"]):
            continue

        video_data[video] = data["upload_date"]

    videos = sorted(video_data.items(), key=lambda x:x[1])
    videos = dict(videos)
    return list(videos.keys())

def upload_video(url, file_path, channel_id):
    data            = ydl.extract_info(url, download=False)
    name            = "".join([i for i in data["title"] if i in chars])
    name            = name.replace(" ", "-")
    name            = "-".join([i for i in name.split("-") if i])
    bid             = 0.01

    data = {
            "method": "publish",
            "params": {
                    "thumbnail_url": data["thumbnail"],
                    "channel_id": channel_id,
                    "file_path": file_path,
                    "title": data["title"],
                    "optimize_file": True,
                    "tags": data["tags"],
                    "bid": str(bid),
                    "name": name
            }
    }
    var = requests.post(host, json=data).json()
    try:
        var = var["result"]["outputs"][0]
        channel = var["signing_channel"]["name"]
        name = var["name"]
        titles.append(data["title"])
        return f"https://lbry.tv/{channel}/{name}"
    except KeyError:
        print(json.dumps(var, indent = 4))
        exit()

def download_video(url):
    filename = os.path.join(os.path.expanduser("~"), "Downloads", url.split("=")[-1])
    filename = filename + ".mp4"
    ydl_opts = {
        "format": "best",
        "outtmpl": filename,
        "noplaylist" : True,
        "quiet": True,
        "retries": 10
    }

    try:
        ydl = YoutubeDL(ydl_opts)
        ydl.download([url])
    except Exception as e:
        e = e.args[0]
        if "encoded url" in e or "404" in e:
            return

        time.sleep(600)
        return download_video(url)

    return filename

def is_uploaded(title:str)-> bool:
    if len(titles):
        if title in titles:
            return True
        else:
            return False
    else:
        data = {
                "method": "claim_list",
                "params": {
                        "claim_type": "stream"
                }
        }
        response_data = requests.post(host, json=data).json()
        response_data = response_data["result"]
        total_pages = response_data["total_pages"]
        for n in range(total_pages + 1):
            data["params"]["page"] = n
            response_data = requests.post(host, json=data).json()
            items = response_data["result"]["items"]
            for item in items:
                titles.append(item["value"]["title"])

    return is_uploaded(title)


def upload_channel(channel, claim_id):
    videos = fetch_videos(channel)
    print(f"Found {len(videos)} videos to upload")
    for video in videos:
        print(f"Downloading {video}")
        file = download_video(video)
        print(f"Video downloaded to {file}")
        print("Uploading video")
        var = upload_video(video, file, claim_id)
        print(f"Video uploaded to {var}")
        time.sleep(300)

if __name__ == "__main__":
    channel = "" #Put youtube channel url
    claim_id = "" #Put claim id of lbry channel, currently you need to create this yourself
    upload_channel(channel, claim_id)
