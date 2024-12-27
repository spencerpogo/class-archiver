# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import re

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import scrapy
from scrapy.pipelines.files import FilesPipeline
from scrapy.http.request import NO_CALLBACK

from .items import CanvasFileItem, PanoptoSessionItem
from .spiders.canvas import CanvasModulesSpider
from .spiders.panopto import PanoptoSpider


class CanvasFilesPipeline(FilesPipeline):
    MEDIA_NAME = "canvas_file"

    def get_media_requests(self, item, info):
        if isinstance(item, CanvasFileItem):
            assert isinstance(
                info.spider, CanvasModulesSpider
            ), f"unknown spider {info.spider!r} returned CanvasFileItem"
            yield scrapy.Request(
                item["download_url"],
                headers=info.spider.canvas.auth_headers(),
                dont_filter=True,  # allow redirects to offsite domains
                callback=NO_CALLBACK,
            )
        return []

    def file_path(self, request, response=None, info=None, *, item=None):
        assert isinstance(info.spider, CanvasModulesSpider)
        course_id = info.spider.course_id
        clean_filename = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "-", item["filename"])
        clean_filename = clean_filename.strip(".")
        assert clean_filename
        return f"export-{course_id}/canvas-files/{item['id']}_{clean_filename}"

    def item_completed(self, results, item, info):
        if isinstance(item, CanvasFileItem):
            item["file_path"] = None
            ok_results = [r for ok, r in results if ok]
            if len(ok_results) > 1:
                raise AssertionError(
                    f"expected at most 1 ok result, got {len(ok_results)}: {results!r}"
                )
            if ok_results:
                (r,) = ok_results
                item["file_path"] = r["path"]
        return item


class PanoptoSessionsPipeline(FilesPipeline):
    MEDIA_NAME = "panopto_session"

    def get_media_requests(self, item, info):
        if isinstance(item, PanoptoSessionItem):
            assert isinstance(
                info.spider, PanoptoSpider
            ), f"unknown spider {info.spider!r} returned PanoptoSessionItem"
            yield scrapy.Request(
                item["srt_url"],
                headers=info.spider.canvas.auth_headers(),
                meta={"panopto_type": "srt"},
                dont_filter=True,
                callback=NO_CALLBACK,
            )
            # this URL requires auth so there is no point in archiving it
            del item["srt_url"]
        return []

    def file_path(self, request, response=None, info=None, *, item=None):
        assert isinstance(info.spider, PanoptoSpider), f"Expected to be scraping from PanoptoSpider"
        course_id = info.spider.course_id
        name = item["name"]
        name = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "-", name).strip(".")
        assert name, f"name is empty: {request}"
        return f"export-{course_id}/panopto-sessions/{name}_{item['id']}.srt"

    def item_completed(self, results, item, info):
        if isinstance(item, PanoptoSessionItem):
            item["srt_path"] = None
            ok_results = [r for ok, r in results if ok]
            if len(ok_results) > 1:
                raise AssertionError(
                    f"expected at most 1 ok result, got {len(ok_results)}: {results!r}"
                )
            if ok_results:
                (r,) = ok_results
                item["srt_path"] = r["path"]
        return item
