#!/usr/bin/env python3

import sys
from yt_dlp import YoutubeDL
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Any
from types import NoneType

USAGE = f"usage: {sys.argv[0]} [-p playlist_link | -v video_link] [-o output_dir]"

@dataclass
class Err:
    exception: Exception
    def __str__(self) -> str:
        return str(self.exception)

def Ok(T):
    @dataclass
    class _OkT:
        value: Optional[T] = None
    return _OkT

def Result(T):
    return (Ok(T) | Err)

OkListOfErr = Ok(List[Err])
OkInt = Ok(int)

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

YoutubeURL = \
    VideoURL | PlaylistURL

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

def error_string(url: str, title: str) -> str:
    return f"Could not download {title} ({url})"

# Returns error code
def download_video(extractor: YoutubeDL, url: str) -> Result(int):
    try:
        return OkInt(extractor.download([url]))
    except Exception as e:
        return Err(e)

# Returns list of failed to download videos or none if info ectraction has fail
def download_from_url(extractor: YoutubeDL, yt_url: YoutubeURL) -> Result(List[Err]):
    match yt_url:
        case VideoURL(url):
            try:
                vid_info = extractor.extract_info(url, download=False)
            except Exception as e:
                return Err(Exception(
                    f"Could not get info from URL: {url}" +  f" due to exception: {e}"
                ))

            download_res = download_video(extractor, url)
            match download_res:
                case OkInt(retcode):
                    if retcode != 1:
                        return OkListOfErr([
                            Err(Exception(error_string(url, vid_info["title"]) + f", retcode: {retcode}"))
                        ])
                    return OkListOfErr([])
                case Err(_):
                    return download_res

        case PlaylistURL(url):
            try:
                pl_info = extractor.extract_info(url, download=False)
            except Exception as e:
                return Err(e)

            entries = pl_info["entries"]
            print(entries)
            errors = []

            for i, e in enumerate(entries):

                if e is None:
                    errors.append(Err(Exception(f"Could not get info on {i} entry in playlist")))
                    continue

                vid_url = e["original_url"]
                download_result = download_video(extractor, vid_url)
                match download_result:
                    case OkInt(retcode):
                        if retcode != 1:
                            errors.append(Err(
                                Exception(
                                    error_string(vid_url, e["title"]) + f", retcode: {retcode}"
                                )
                            ))

                    case Err(e):
                        errors.append(Err(
                            Exception(
                                error_string(vid_url, e["title"]) +  f" due to exception: {e}"
                            )
                        ))
            return OkListOfErr(errors)

        case _:
            return Err(ValueError("Wrong type for yt_url argument"))

def main():
    if len(sys.argv) < 3:
        print(USAGE)
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
        print(USAGE)
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

    download_res = download_from_url(extractor, url)

    match download_res:
        case OkListOfErr(errors):
            if len(errors) > 0:
                print(
                    "Wasn't able to download:\n" +
                    "\n------------------------\n"
                        .join(str(er) for er in errors)
                )
        case Err(e):
            print(f"Could not download video from URL due error: {e}")
            return 69

    return 0

if __name__ == "__main__":
    exit(main())