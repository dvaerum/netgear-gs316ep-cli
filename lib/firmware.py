import io
import re
from datetime import timedelta
from time import sleep, time
from typing import List
from zipfile import ZipFile

import requests
from bs4 import BeautifulSoup

from .client import Client
from .misc import bad_request


def _version2int(version: str) -> List[int]:
    version_int = []
    for v in version.split("."):
        version_int.append(int(v))
    return version_int


def update_time(client: Client) -> timedelta:
    resp = client.get("/iss/specific/dashboard.html", timeout=10)
    bs = BeautifulSoup(resp.text, 'html.parser')
    uptime_element = bs.find('div', id="timezone-area").find_next_sibling()
    uptime_string = uptime_element.find('span').decode_contents().strip()
    result = re.search(
        r"(?P<hours>[0-9]+) *hrs, *(?P<minutes>[0-9]+) *mins, *(?P<seconds>[0-9]+) *secs",
        uptime_string, re.IGNORECASE,
    )
    if not result:
        raise Exception("Was not able to get uptime")

    result_g = result.groupdict()
    return timedelta(hours=int(result_g['hours']), minutes=int(result_g['minutes']), seconds=int(result_g['seconds']))


def update(client: Client, reboot_wait_sec: int = 600):
    update_time_start = time()
    resp = client.get("/iss/specific/firmware.html")

    bs = BeautifulSoup(resp.text, 'html.parser')
    version_str = bs.find('span', attrs={"class": "firm-data"}).next_element
    if version_str.split(".").__len__() != 4:
        raise Exception("Version format is unknown")

    # https://www.netgear.com/support/product/gs316ep/#download
    official_resp = requests.get(
        "https://www.netgear.com/api/v2/product/getproductdetails?componentId=117073&publicationId=11")
    available_versions_json = official_resp.json()

    latest_versions_obj_raw = available_versions_json.get(
        'data', {}).get('typedComponent', {}).get('downloadMap', {}).get('latest')

    latest_versions_obj = [
        x.get('content', {}).get('data')
        for x in latest_versions_obj_raw
        if 'firmware' in x.get('content', {}).get('data', {}).get('title', '').lower()
    ]

    if not latest_versions_obj:
        raise Exception("No latest version located")

    latest_version_obj = latest_versions_obj[0]
    latest_version_str = latest_version_obj.get('title', '').split(" ")[-1]
    latest_version_url = latest_version_obj.get('url')
    if latest_version_str.split(".").__len__() != 4:
        raise Exception("Latest version format from the official website (netgear.com) is unknown")

    if latest_version_url is None:
        raise Exception("The URL to the latest version from the official website (netgear.com) is unknown")

    version_int = _version2int(version_str)
    latest_version_int = _version2int(latest_version_str)
    if not _version2int(version_str) < _version2int(latest_version_str):
        return {"status_code": 0, "status_code": "No new updates", "update_time_sec": time() - update_time_start,
                "old_version_str": version_str, "old_version_int": version_int,
                "new_version_str": latest_version_str, "new_version_int": latest_version_int}

    latest_version_firmware_data = requests.get(latest_version_url)

    zip_file_content = io.BytesIO(latest_version_firmware_data.content)

    zip_file = ZipFile(zip_file_content)
    zip_file_content_objs_firmware = [x for x in zip_file.filelist if x.filename.lower().endswith(".image")]
    if zip_file_content_objs_firmware.__len__() != 1:
        raise Exception("Was unable to located the firmware file in the zip file "
                        "download from the official website (netgear.com)")

    zip_file_content_obj_firmware = zip_file_content_objs_firmware[0]
    latest_firmware_raw_data = zip_file.read(zip_file_content_obj_firmware.filename)

    uptime_before_update = update_time(client)

    # The upload takes around 3 mins
    resp_upload_firmware = client.post("/iss/file/post/image1", files={
        "Gambit": (None, client.get_token()),
        "fileField": (zip_file_content_obj_firmware.filename, latest_firmware_raw_data, 'application/octet-stream'),
    })
    bs_upload_firmware = BeautifulSoup(resp_upload_firmware.text, 'html.parser')
    if (resp_upload_firmware.status_code != 200 or
        bs_upload_firmware.find("span", attrs={"class": "heading-1"}).next_element != "FIRMWARE"):
        bad_request(resp_upload_firmware, msg="Bad Request - Firmware update failed")

    # The switch reboot after firmware update, so wait for it to come online again
    sleep(5)
    reboot_wait_time_start = time()
    while True:
        if reboot_wait_time_start + reboot_wait_sec > time():
            TimeoutError(f"It is more when {reboot_wait_sec} seconds since the switch was update and rebooted")

        try:
            if client.valid_token() is False:
                client.login()
            uptime_after_update = update_time(client)
            if uptime_after_update < uptime_before_update:
                break
            else:
                print("DEBUG: Have not rebooted after the update, yet!")
        except (TimeoutError, ConnectionAbortedError) as _err:
            pass
        except Exception as err:
            print(f"DEBUG: HTTP Request failed - err: {err}")

    resp_new_version = client.get("/iss/specific/firmware.html")
    bs_new_version = BeautifulSoup(resp_new_version.text, 'html.parser')
    new_version_str = bs_new_version.find('span', attrs={"class": "firm-data"}).next_element
    return {"status_code": 1, "status_code": "Updated firmware", "update_time_sec": time() - update_time_start,
            "old_version_str": version_str, "old_version_int": version_int,
            "new_version_str": new_version_str, "new_version_int": _version2int(new_version_str)}
