from typing import Dict, List, Optional

class WebResult:
    def __init__(self, id: str, name: str, url: str, display_url: str, snippet: str, date_last_crawled: str, language: str, is_navigational: bool, contractual_rules: Optional[List[Dict]] = None):
        self.id = id
        self.name = name
        self.url = url
        self.display_url = display_url
        self.snippet = snippet
        self.date_last_crawled = date_last_crawled
        self.language = language
        self.is_navigational = is_navigational
        self.contractual_rules = contractual_rules

    def __repr__(self):
        return f"WebResult(id={self.id}, name={self.name}, url={self.url}, display_url={self.display_url}, snippet={self.snippet}, date_last_crawled={self.date_last_crawled}, language={self.language}, is_navigational={self.is_navigational}, contractual_rules={self.contractual_rules})"

