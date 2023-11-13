#!/usr/bin/env python3

import sys
from yt_dlp import YoutubeDL
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Opt:
    opt: str
    arg: Optional[str] = None

@dataclass
class VideoURL:
    url: str
    title: Optional[str] = None

@dataclass
class PlaylistURL:
    url: str

YoutubeURL = (
    VideoURL | 
    PlaylistURL
) 

def get_opts(args: List[str]) -> List[Opt]:
    lst = []
    last = None
    while args:
        nxt = args.pop()
        if nxt.startswith("-"):
            lst.append(Opt(nxt[1::], last))
            last = None
        else:
            last = nxt
    return lst


USAGE = f"usage: {sys.argv[0]} [-p playlist_link] [-v video_link] [-o output_dir]"

# Returns error code
def download_video(extractor: YoutubeDL, url: VideoURL) -> int:
    return extractor.download([url.url])

# Returns list of failed to download videos or none if info ectraction has fail
def download_from_url(extractor: YoutubeDL, url: YoutubeURL) -> Optional[List[VideoURL]]:
    match url:
        case VideoURL(_):
            try:
                vid_info = extractor.extract_info(url.url, download=False )
                error_code = download_video(extractor, url)
                if error_code:
                    return [VideoURL(url, vid_info["title"])]
                return []
            except:
                return None
        case PlaylistURL(url_str):
            try:
                pl_info = extractor.extract_info(url_str, download=False)
            except:
                return None

            entries = pl_info["entries"]
            return [
                VideoURL(e["original_url"], e["title"]) for e in entries 
                if download_video(extractor, VideoURL(e["original_url"]))
            ]
        case _:
            return None

def main():
    if len(sys.argv) < 3:
        return 64

    lib_dir = Path("./lib") 
    url: Optional[YoutubeURL] = None

    opts = get_opts(sys.argv[1::])

    for opt in opts:
        match opt:
            case Opt("p", arg):
                url = PlaylistURL(arg) if arg else None
            case Opt("v", arg):
                url = VideoURL(arg) if arg else None
            case Opt("o", arg):
                lib_dir = Path(arg) if arg else None    

    if (not url) or (not lib_dir):
        return 64

    extractor = YoutubeDL( {
        'format': 'm4a/bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }],
        "paths": {"home": str(lib_dir.absolute())},
        "ignoreerrors": True
    } )

    not_dowloaded = download_from_url(extractor, url)

    if not_dowloaded is None:
        return 69

    if not not_dowloaded:
        print(
            "Unable to download:\n" + 
            "\n------------------------\n"
                .join(f"URL: {e.url}\nTitle: {e.title}" for e in not_dowloaded)
        )

    return 0

if __name__ == "__main__":
    exit(main())