
class Utils:
    def escape_prompt_content(content):
        return content.replace('{', '{{').replace('}', '}}')
