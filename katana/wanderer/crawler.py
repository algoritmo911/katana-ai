from .guardian import GuardianProxy

class AsyncCrawler:
    def __init__(self, guardian: GuardianProxy):
        self.guardian = guardian
        # Здесь будет инициализация Playwright

    async def fetch(self, url: str) -> str:
        """
        Получает контент страницы, используя наилучшую стратегию.
        """
        # Псевдокод:
        # if is_javascript_heavy(url):
        #   content = await self.fetch_with_playwright(url)
        # else:
        #   response = await self.guardian.request("GET", url)
        #   content = response.text
        # return content

        # Пока что простая реализация:
        response = await self.guardian.request("GET", url)
        return response.text
