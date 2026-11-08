"""分页工具."""
from django.utils.safestring import mark_safe


class Pagination:
    """简单分页器."""

    def __init__(self, queryset, page_number, page_size=10, show_pages=7, request=None):
        self.page_size = page_size
        self.show_pages = show_pages
        self.request = request
        self.total = queryset.count()
        self.total_pages = max(1, (self.total + page_size - 1) // page_size)
        try:
            self.page_number = int(page_number)
        except (ValueError, TypeError):
            self.page_number = 1
        if self.page_number < 1:
            self.page_number = 1
        if self.page_number > self.total_pages:
            self.page_number = self.total_pages

        start = (self.page_number - 1) * page_size
        self.object_list = queryset[start:start + page_size]

    @property
    def has_previous(self):
        return self.page_number > 1

    @property
    def has_next(self):
        return self.page_number < self.total_pages

    @property
    def previous_page_number(self):
        return self.page_number - 1

    @property
    def next_page_number(self):
        return self.page_number + 1

    def page_range(self):
        half = self.show_pages // 2
        start = max(1, self.page_number - half)
        end = min(self.total_pages, start + self.show_pages - 1)
        start = max(1, end - self.show_pages + 1)
        return range(start, end + 1)

    def make_url(self, page):
        """生成保留当前筛选条件的分页链接."""
        if self.request is None:
            return f"?page={page}"
        params = {k: v for k, v in self.request.GET.items() if k != "page"}
        params["page"] = page
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.request.path}?{query}"

    @property
    def html(self):
        """生成分页 HTML（模板中直接 {{ pagination.html }} 使用）."""
        if self.total_pages <= 1:
            return ""
        html = ['<nav><ul class="pagination">']
        if self.has_previous:
            html.append(f'<li><a href="{self.make_url(self.previous_page_number)}">&laquo;</a></li>')
        else:
            html.append('<li class="disabled"><span>&laquo;</span></li>')

        for p in self.page_range():
            cls = "active" if p == self.page_number else ""
            html.append(f'<li class="{cls}"><a href="{self.make_url(p)}">{p}</a></li>')

        if self.has_next:
            html.append(f'<li><a href="{self.make_url(self.next_page_number)}">&raquo;</a></li>')
        else:
            html.append('<li class="disabled"><span>&raquo;</span></li>')

        html.append("</ul></nav>")
        return mark_safe("".join(html))
