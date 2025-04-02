import json
import re
def syntax_highlight(json_file):
    if not isinstance (json_file, str):
        json_file=json.dumps(json_file, indent=2)
    json_file= (
        json_file.replace("&", "&amp;")
        .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    def replacer(match):
        match_text = match.group(0)
        
        if re.match(r'^"(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"\s*:', match_text):
            return f'<span class="key">{match_text}</span>'
        elif re.match(r'^"', match_text):
            return f'<span class="string">{match_text}</span>'
        elif re.match(r'\b(true|false)\b', match_text):
            return f'<span class="boolean">{match_text}</span>'
        elif re.match(r'\bnull\b', match_text):
            return f'<span class="null">{match_text}</span>'
        elif re.match(r'-?\d+(\.\d*)?(e[+-]?\d+)?', match_text):
            return f'<span class="number">{match_text}</span>'
        elif re.match(r'[{}\[\]]', match_text):
            return f'<span class="bracket">{match_text}</span>'
        
        return match_text
    
    pattern = r'("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"\s*:|"(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"|\b(true|false|null)\b|-?\d+(\.\d*)?(e[+-]?\d+)?|[{}\[\]])'
    
    return re.sub(pattern, replacer, json_obj)
